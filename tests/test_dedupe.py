import unittest
from src.dedupe import generate_fingerprint, is_new_record, add_to_seen
from src.models import NormalizedTradeRecord

class TestDedupe(unittest.TestCase):
    def test_generate_fingerprint(self):
        record: NormalizedTradeRecord = {
            "source_chamber": "senate",
            "symbol": "NVDA",
            "issuer": "NVIDIA Corp",
            "politician_name": "Jane Doe",
            "transaction_type": "Purchase",
            "transaction_date": "2026-04-01",
            "disclosure_date": "2026-04-20",
            "amount_range": "$1,001-$15,000",
            "owner": "Self",
            "link": None,
            "raw_record": {}
        }
        fp = generate_fingerprint(record)
        self.assertIsInstance(fp, str)
        self.assertEqual(len(fp), 64)  # SHA256 hex

    def test_is_new_record(self):
        record = {
            "source_chamber": "senate",
            "symbol": "NVDA",
            "issuer": "NVIDIA Corp",
            "politician_name": "Jane Doe",
            "transaction_type": "Purchase",
            "transaction_date": "2026-04-01",
            "disclosure_date": "2026-04-20",
            "amount_range": "$1,001-$15,000",
            "owner": "Self",
            "link": None,
            "raw_record": {}
        }
        seen = set()
        self.assertTrue(is_new_record(record, seen))
        add_to_seen(record, seen)
        self.assertFalse(is_new_record(record, seen))

if __name__ == "__main__":
    unittest.main()