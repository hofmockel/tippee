import logging
from datetime import datetime
from typing import Dict, Any, List
from .models import NormalizedTradeRecord

logger = logging.getLogger(__name__)

def normalize_date(date_str: str) -> str:
    """Normalize date string to YYYY-MM-DD."""
    try:
        # Try parsing common formats
        for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y"]:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
        # If none match, return as is or log
        logger.warning(f"Could not parse date: {date_str}")
        return date_str
    except Exception as e:
        logger.warning(f"Error normalizing date {date_str}: {e}")
        return date_str

def normalize_transaction_type(tx_type: str) -> str:
    """Normalize transaction type to canonical set."""
    tx_type = tx_type.lower()
    if "purchase" in tx_type or "buy" in tx_type:
        return "Purchase"
    elif "sale" in tx_type or "sell" in tx_type:
        return "Sale"
    elif "exchange" in tx_type:
        return "Exchange"
    else:
        return "Other"

def normalize_owner(owner: str) -> str:
    """Normalize owner to canonical set."""
    owner = owner.lower()
    if "self" in owner:
        return "Self"
    elif "spouse" in owner:
        return "Spouse"
    elif "dependent" in owner or "child" in owner:
        return "Dependent Child"
    else:
        return "Unknown"

def normalize_record(raw: Dict[str, Any], chamber: str) -> NormalizedTradeRecord | None:
    """Normalize a raw record from FMP."""
    try:
        # Assuming FMP fields; adjust if needed
        symbol = raw.get("symbol", "").upper()
        issuer = raw.get("company", raw.get("issuer", ""))
        politician_name = raw.get("senator", raw.get("representative", raw.get("politician", "")))
        transaction_type = normalize_transaction_type(raw.get("transactionType", raw.get("type", "")))
        transaction_date = normalize_date(raw.get("transactionDate", raw.get("tradeDate", "")))
        disclosure_date = normalize_date(raw.get("disclosureDate", raw.get("reportDate", "")))
        amount_range = raw.get("amount", raw.get("amountRange", ""))
        owner = normalize_owner(raw.get("owner", ""))
        link = raw.get("url", raw.get("link", None))

        if not symbol or not politician_name:
            logger.warning(f"Skipping record with missing symbol or politician: {raw}")
            return None

        return {
            "source_chamber": chamber,
            "symbol": symbol,
            "issuer": issuer,
            "politician_name": politician_name,
            "transaction_type": transaction_type,
            "transaction_date": transaction_date,
            "disclosure_date": disclosure_date,
            "amount_range": amount_range,
            "owner": owner,
            "link": link,
            "raw_record": raw
        }
    except Exception as e:
        logger.warning(f"Error normalizing record: {e}, raw: {raw}")
        return None

def normalize_records(raw_records: List[Dict[str, Any]], chamber: str) -> List[NormalizedTradeRecord]:
    """Normalize a list of raw records."""
    normalized = []
    for raw in raw_records:
        norm = normalize_record(raw, chamber)
        if norm:
            normalized.append(norm)
    return normalized