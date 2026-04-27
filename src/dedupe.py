import hashlib
import json
import logging
from typing import Set
from .models import NormalizedTradeRecord

logger = logging.getLogger(__name__)

# Field order is part of the fingerprint contract. Changing it (or the
# canonicalization below) invalidates every entry in data/seen_hashes.json.
_FINGERPRINT_FIELDS = (
    "source_chamber",
    "symbol",
    "politician_name",
    "transaction_type",
    "transaction_date",
    "disclosure_date",
    "amount_range",
    "owner",
)


def generate_fingerprint(record: NormalizedTradeRecord) -> str:
    """Generate a deterministic fingerprint for a record.

    Uses JSON canonical encoding so a literal `|` (or any other character) in
    a field can't shift bytes between fields and collide with a different
    record. Replaces the previous `|`-joined scheme; see _legacy_fingerprint.
    """
    payload = json.dumps(
        [record[f] for f in _FINGERPRINT_FIELDS],
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _legacy_fingerprint(record: NormalizedTradeRecord) -> str:
    """Pre-JSON fingerprint scheme. Kept so that existing seen_hashes entries
    written by older versions still suppress alerts after upgrade. Coerces
    None / non-string values so this fallback can never crash dedupe (the
    JSON-based scheme above already handles them via json.dumps)."""
    parts = ("" if record[f] is None else str(record[f]) for f in _FINGERPRINT_FIELDS)
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def is_new_record(record: NormalizedTradeRecord, seen_hashes: Set[str]) -> bool:
    """Check if the record is new under either the current or legacy scheme."""
    return (
        generate_fingerprint(record) not in seen_hashes
        and _legacy_fingerprint(record) not in seen_hashes
    )


def add_to_seen(record: NormalizedTradeRecord, seen_hashes: Set[str]) -> None:
    """Add the record's fingerprint to seen hashes (current scheme only)."""
    seen_hashes.add(generate_fingerprint(record))
