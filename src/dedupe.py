import hashlib
import logging
from typing import Set
from .models import NormalizedTradeRecord

logger = logging.getLogger(__name__)

def generate_fingerprint(record: NormalizedTradeRecord) -> str:
    """Generate a deterministic fingerprint for a record."""
    key = "|".join([
        record["source_chamber"],
        record["symbol"],
        record["politician_name"],
        record["transaction_type"],
        record["transaction_date"],
        record["disclosure_date"],
        record["amount_range"],
        record["owner"]
    ])
    return hashlib.sha256(key.encode()).hexdigest()

def is_new_record(record: NormalizedTradeRecord, seen_hashes: Set[str]) -> bool:
    """Check if the record is new."""
    fp = generate_fingerprint(record)
    return fp not in seen_hashes

def add_to_seen(record: NormalizedTradeRecord, seen_hashes: Set[str]) -> None:
    """Add the record's fingerprint to seen hashes."""
    fp = generate_fingerprint(record)
    seen_hashes.add(fp)