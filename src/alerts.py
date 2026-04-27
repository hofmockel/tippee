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


def send_discord_alert(record: NormalizedTradeRecord, webhook_url: str) -> bool:
    """POST a disclosure alert to Discord. Returns True on success.

    Honours Discord's 429 Retry-After so a bursty disclosure day doesn't drop
    alerts. All other errors return False after a single attempt — the caller
    is expected to leave the record unmarked so the next run retries.
    """
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
    payload = {"content": message}
    for attempt in range(_MAX_DISCORD_RETRIES):
        try:
            response = httpx.post(webhook_url, json=payload, timeout=10)
            if response.status_code == 429:
                delay = _parse_retry_after(response)
                logger.warning(
                    "Discord rate limited (attempt %s/%s); sleeping %.2fs",
                    attempt + 1, _MAX_DISCORD_RETRIES, delay,
                )
                time.sleep(delay)
                continue
            response.raise_for_status()
            logger.info(f"Discord alert sent for {record['symbol']}")
            return True
        except Exception as e:
            logger.error(f"Failed to send Discord alert: {e}")
            return False
    logger.error("Failed to send Discord alert: rate-limited beyond retries")
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
    """Send an end-of-run heartbeat. Logs the message regardless; posts to Discord if a webhook is set."""
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
    try:
        response = httpx.post(webhook_url, json={"content": message}, timeout=10)
        response.raise_for_status()
        logger.info("Run confirmation alert sent")
    except Exception as e:
        logger.error(f"Failed to send run confirmation alert: {e}")
