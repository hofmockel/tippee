import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from .config import Config
from .storage import Storage
from .client import FMPClient
from .normalize import normalize_records
from .dedupe import is_new_record, add_to_seen
from .alerts import alert_new_record
from .models import NormalizedTradeRecord

def setup_logging(log_level: str):
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("logs/app.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )

def run_scan(config: Config, send_alerts: bool = True) -> None:
    logger = logging.getLogger(__name__)
    logger.info("Starting run")

    watchlist = config.load_watchlist()
    if not watchlist:
        logger.warning("No symbols in watchlist")
        return

    client = FMPClient(config.fmp_api_key, config.request_timeout_seconds, config.max_retries)
    seen_hashes = Storage.load_seen_hashes()
    new_records = []

    total_fetched = 0

    for symbol in watchlist:
        try:
            senate_data = client.get_senate_trades(symbol)
            house_data = client.get_house_trades(symbol)

            senate_normalized = normalize_records(senate_data, "senate")
            house_normalized = normalize_records(house_data, "house")

            all_records = senate_normalized + house_normalized
            total_fetched += len(all_records)

            for record in all_records:
                if is_new_record(record, seen_hashes):
                    new_records.append(record)
                    add_to_seen(record, seen_hashes)
                    if send_alerts:
                        alert_new_record(record, config.discord_webhook_url)
                else:
                    add_to_seen(record, seen_hashes)  # still add to seen for audit

        except Exception as e:
            logger.error(f"Failed to process symbol {symbol}: {e}")
            continue

    Storage.save_seen_hashes(seen_hashes)
    Storage.save_last_run({
        "timestamp": datetime.now().isoformat(),
        "fetched_records": total_fetched,
        "new_records": len(new_records)
    })

    logger.info(f"Run complete: fetched {total_fetched} records, {len(new_records)} new")

def test_alert(config: Config) -> None:
    logger = logging.getLogger(__name__)
    logger.info("Sending test alert")

    # Sample record
    sample: NormalizedTradeRecord = {
        "source_chamber": "house",
        "symbol": "TEST",
        "issuer": "Test Corp",
        "politician_name": "Test Politician",
        "transaction_type": "Purchase",
        "transaction_date": "2026-04-01",
        "disclosure_date": "2026-04-20",
        "amount_range": "$1,001-$15,000",
        "owner": "Self",
        "link": None,
        "raw_record": {}
    }

    alert_new_record(sample, config.discord_webhook_url)

def backfill(config: Config, days: int) -> None:
    # For backfill, we assume fetching current data is sufficient, as FMP has historical
    # But since endpoints are per symbol, and no date param, we just fetch current
    logger = logging.getLogger(__name__)
    logger.info(f"Starting backfill for {days} days (fetching current data)")

    run_scan(config, send_alerts=False)

def main():
    parser = argparse.ArgumentParser(description="Congressional Trade Watcher")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("run", help="Perform one normal daily scan")
    subparsers.add_parser("test-alert", help="Send a sample Discord alert")
    backfill_parser = subparsers.add_parser("backfill", help="Fetch data and populate seen_hashes without alerts")
    backfill_parser.add_argument("--days", type=int, default=30, help="Number of days to backfill")

    args = parser.parse_args()

    config = Config()
    setup_logging(config.log_level)

    if args.command == "run":
        run_scan(config)
    elif args.command == "test-alert":
        test_alert(config)
    elif args.command == "backfill":
        backfill(config, args.days)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()