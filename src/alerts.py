import logging
import httpx
from .models import NormalizedTradeRecord

logger = logging.getLogger(__name__)

def send_discord_alert(record: NormalizedTradeRecord, webhook_url: str) -> bool:
    """Send a Discord alert for a new record."""
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
    try:
        response = httpx.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info(f"Discord alert sent for {record['symbol']}")
        return True
    except Exception as e:
        logger.error(f"Failed to send Discord alert: {e}")
        return False

def send_console_alert(record: NormalizedTradeRecord) -> None:
    """Log the alert to console."""
    logger.info(f"New disclosure: {record['symbol']} by {record['politician_name']} ({record['source_chamber']})")

def alert_new_record(record: NormalizedTradeRecord, discord_url: str) -> None:
    """Send alerts for a new record."""
    send_console_alert(record)
    if discord_url:
        send_discord_alert(record, discord_url)

def send_run_confirmation(total_fetched: int, new_records: int, message_template: str, webhook_url: str) -> bool:
    """Send an end-of-run proof-of-life ping to Discord. Used when a run completes with no new disclosures."""
    if not webhook_url:
        return False
    try:
        message = message_template.format(total_fetched=total_fetched, new_records=new_records)
    except (KeyError, IndexError) as e:
        logger.error(f"Bad CONFIRMATION_MESSAGE template: {e}")
        return False
    try:
        response = httpx.post(webhook_url, json={"content": message}, timeout=10)
        response.raise_for_status()
        logger.info("Run confirmation sent to Discord")
        return True
    except Exception as e:
        logger.error(f"Failed to send run confirmation: {e}")
        return False