import unittest
from src.normalize import normalize_record, normalize_transaction_type, normalize_owner, normalize_date

class TestNormalize(unittest.TestCase):
    def test_normalize_transaction_type(self):
        self.assertEqual(normalize_transaction_type("Purchase"), "Purchase")
        self.assertEqual(normalize_transaction_type("sale"), "Sale")
        self.assertEqual(normalize_transaction_type("exchange"), "Exchange")
        self.assertEqual(normalize_transaction_type("unknown"), "Other")

    def test_normalize_owner(self):
        self.assertEqual(normalize_owner("Self"), "Self")
        self.assertEqual(normalize_owner("spouse"), "Spouse")
        self.assertEqual(normalize_owner("dependent child"), "Dependent Child")
        self.assertEqual(normalize_owner("other"), "Unknown")

    def test_normalize_date(self):
        self.assertEqual(normalize_date("2026-04-01"), "2026-04-01")
        self.assertEqual(normalize_date("04/01/2026"), "2026-04-01")

    def test_normalize_record(self):
        raw = {
            "symbol": "nvda",
            "company": "NVIDIA Corp",
            "senator": "Jane Doe",
            "transactionType": "Purchase",
            "transactionDate": "2026-04-01",
            "disclosureDate": "2026-04-20",
            "amount": "$1,001-$15,000",
            "owner": "Self"
        }
        record = normalize_record(raw, "senate")
        self.assertIsNotNone(record)
        self.assertEqual(record["symbol"], "NVDA")
        self.assertEqual(record["source_chamber"], "senate")

if __name__ == "__main__":
    unittest.main()