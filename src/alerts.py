import logging
import time
import httpx
from .models import NormalizedTradeRecord

logger = logging.getLogger(__name__)

# Discord webhook responses on 429 include a Retry-After header (seconds, may
# be fractional) and/or a JSON body with retry_after. We retry up to this many
# times before giving up.
_MAX_DISCORD_RETRIES = 3
_MAX_RETRY_AFTER_SECONDS = 60.0


def _parse_retry_after(response: httpx.Response) -> float:
    """Best-effort extraction of Retry-After from a Discord 429 response."""
    header = response.headers.get("Retry-After") or response.headers.get("retry-after")
    if header:
        try:
            return min(float(header), _MAX_RETRY_AFTER_SECONDS)
        except ValueError:
            pass
    try:
        body = response.json()
    except Exception:
        body = {}
    body_value = body.get("retry_after") if isinstance(body, dict) else None
    if body_value is not None:
        try:
            return min(float(body_value), _MAX_RETRY_AFTER_SECONDS)
        except (TypeError, ValueError):
            pass
    return 1.0


def _post_to_discord(webhook_url: str, payload: dict, what: str) -> bool:
    """POST `payload` to a Discord webhook with 429 + 5xx retry.

    Honours Discord's 429 Retry-After and retries 5xx with exponential backoff
    so transient outages and bursty disclosure bursts don't drop messages. 4xx
    other than 429 fail-fast (caller error). Returns True on success, False
    after retries are exhausted or on any non-retryable error.

    `what` is a short label included in log lines for context (e.g.
    "alert for NVDA", "run confirmation").
    """
    for attempt in range(_MAX_DISCORD_RETRIES):
        try:
            response = httpx.post(webhook_url, json=payload, timeout=10)
            if response.status_code == 429:
                delay = _parse_retry_after(response)
                logger.warning(
                    "Discord rate limited (%s, attempt %s/%s); sleeping %.2fs",
                    what, attempt + 1, _MAX_DISCORD_RETRIES, delay,
                )
                time.sleep(delay)
                continue
            if 500 <= response.status_code < 600:
                delay = min(2 ** attempt, _MAX_RETRY_AFTER_SECONDS)
                logger.warning(
                    "Discord %s (%s, attempt %s/%s); backing off %.2fs",
                    response.status_code, what, attempt + 1, _MAX_DISCORD_RETRIES, delay,
                )
                time.sleep(delay)
                continue
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error("Failed to send Discord %s: %s", what, e)
            return False
    logger.error("Failed to send Discord %s: retries exhausted", what)
    return False


def send_discord_alert(record: NormalizedTradeRecord, webhook_url: str) -> bool:
    """POST a disclosure alert to Discord. Returns True on success."""
    message = f"""New congressional trade disclosure detected

Symbol: {record["symbol"]}
Chamber: {record["source_chamber"].capitalize()}
Politician: {record["politician_name"]}
Type: {record["transaction_type"]}
Trade date: {record["transaction_date"]}
Disclosure date: {record["disclosure_date"]}
Amount: {record["amount_range"]}
Owner: {record["owner"]}
"""
    if _post_to_discord(webhook_url, {"content": message}, f"alert for {record['symbol']}"):
        logger.info(f"Discord alert sent for {record['symbol']}")
        return True
    return False


def send_console_alert(record: NormalizedTradeRecord) -> None:
    """Log the alert to console."""
    logger.info(f"New disclosure: {record['symbol']} by {record['politician_name']} ({record['source_chamber']})")


def alert_new_record(record: NormalizedTradeRecord, discord_url: str) -> bool:
    """Send alerts for a new record. Returns True if delivery succeeded
    (or there was no Discord webhook to deliver to). Returns False only when
    a Discord post was attempted and failed."""
    send_console_alert(record)
    if not discord_url:
        return True
    return send_discord_alert(record, discord_url)


def send_run_confirmation(
    total_fetched: int,
    new_records: int,
    confirmation_message_template: str,
    webhook_url: str,
) -> None:
    """Send an end-of-run heartbeat. Logs the message regardless; posts to
    Discord (with the same 429 + 5xx retry handling as disclosure alerts) if a
    webhook is set."""
    try:
        message = confirmation_message_template.format(
            total_fetched=total_fetched,
            new_records=new_records,
        )
    except (KeyError, IndexError) as e:
        logger.error(f"Bad CONFIRMATION_MESSAGE template: {e}")
        return
    logger.info(message)
    if not webhook_url:
        return
    if _post_to_discord(webhook_url, {"content": message}, "run confirmation"):
        logger.info("Run confirmation alert sent")
