import logging
from datetime import datetime
from typing import Dict, Any, List, Tuple
from .models import NormalizedTradeRecord

logger = logging.getLogger(__name__)

def normalize_date(date_str: str) -> str:
    """Normalize date string to YYYY-MM-DD.

    Tries ISO 8601 (FMP's standard for several endpoints, including the
    `T00:00:00.000Z` form) first, then the legacy formats. fromisoformat in
    3.11+ handles trailing `Z` natively.
    """
    if not date_str:
        return ""
    try:
        return datetime.fromisoformat(date_str).strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        pass
    for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y"]:
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    logger.warning(f"Could not parse date: {date_str}")
    return date_str

def normalize_transaction_type(tx_type: str) -> str:
    """Normalize transaction type to canonical set."""
    tx_type = (tx_type or "").lower()
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
    owner = (owner or "").lower()
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
    # Identifier used only in error logs to avoid dumping the full raw record
    # (which can contain free-text politician names, internal IDs, etc.) into
    # logs that may end up in CI artifacts.
    log_id = (raw.get("symbol") or "?")
    try:
        symbol = (raw.get("symbol") or "").upper()
        issuer = raw.get("company") or raw.get("issuer") or ""
        politician_name = raw.get("senator") or raw.get("representative") or raw.get("politician") or ""
        transaction_type = normalize_transaction_type(raw.get("transactionType") or raw.get("type") or "")
        transaction_date = normalize_date(raw.get("transactionDate") or raw.get("tradeDate") or "")
        disclosure_date = normalize_date(raw.get("disclosureDate") or raw.get("reportDate") or "")
        amount_range = raw.get("amount") or raw.get("amountRange") or ""
        owner = normalize_owner(raw.get("owner") or "")
        link = raw.get("url") or raw.get("link") or None

        if not symbol or not politician_name:
            logger.warning("Skipping record with missing symbol or politician (id=%s)", log_id)
            return None
        if not transaction_date or not disclosure_date:
            # Empty dates would collide in the dedupe fingerprint with other
            # missing-date records from the same politician+symbol.
            logger.warning(
                "Skipping record with missing date(s) (symbol=%s politician=%s)",
                symbol, politician_name,
            )
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
        logger.warning("Error normalizing record (id=%s): %s", log_id, e)
        return None

def normalize_records(
    raw_records: List[Dict[str, Any]], chamber: str
) -> Tuple[List[NormalizedTradeRecord], int]:
    """Normalize a list of raw records. Returns (records, dropped_count).

    Dropped count covers anything `normalize_record` returned None for —
    missing required fields, malformed dates, exception during normalization.
    Caller is expected to surface the count so silent data loss is visible.
    """
    normalized: List[NormalizedTradeRecord] = []
    dropped = 0
    for raw in raw_records:
        norm = normalize_record(raw, chamber)
        if norm:
            normalized.append(norm)
        else:
            dropped += 1
    return normalized, dropped