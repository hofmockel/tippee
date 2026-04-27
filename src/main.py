import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from .config import Config
from .storage import Storage
from .client import FMPClient
from .normalize import normalize_records
from .dedupe import is_new_record, add_to_seen
from .alerts import alert_new_record, send_run_confirmation
from .models import NormalizedTradeRecord

def setup_logging(log_level: str):
    Path("logs").mkdir(parents=True, exist_ok=True)
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

    seen_hashes = Storage.load_seen_hashes()
    new_records = []
    total_fetched = 0

    with FMPClient(config.fmp_api_key, config.request_timeout_seconds, config.max_retries) as client:
        for symbol in watchlist:
            senate_data = []
            house_data = []
            try:
                senate_data = client.get_senate_trades(symbol)
            except Exception as e:
                logger.error(f"Failed to fetch senate trades for {symbol}: {e}")
            try:
                house_data = client.get_house_trades(symbol)
            except Exception as e:
                logger.error(f"Failed to fetch house trades for {symbol}: {e}")

            all_records = (
                normalize_records(senate_data, "senate")
                + normalize_records(house_data, "house")
            )
            total_fetched += len(all_records)

            for record in all_records:
                if is_new_record(record, seen_hashes):
                    new_records.append(record)
                    if send_alerts and not config.send_disclosure_alerts:
                        # Toggle off in run mode: silence the alert AND leave
                        # the record unseen, so re-enabling delivers it later.
                        continue
                    if not send_alerts:
                        # Backfill: mark seen without alerting.
                        add_to_seen(record, seen_hashes)
                        continue
                    # run mode with alerts on: only mark seen if delivery
                    # succeeded, so a Discord failure leaves the record for
                    # the next run to retry.
                    if alert_new_record(record, config.discord_webhook_url):
                        add_to_seen(record, seen_hashes)
                else:
                    add_to_seen(record, seen_hashes)  # idempotent; keeps already-seen records seen

    Storage.save_seen_hashes(seen_hashes)
    Storage.save_last_run({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "fetched_records": total_fetched,
        "new_records": len(new_records)
    })

    logger.info(f"Run complete: fetched {total_fetched} records, {len(new_records)} new")

    if send_alerts and len(new_records) == 0 and config.send_confirmation_alert:
        send_run_confirmation(
            total_fetched,
            len(new_records),
            config.confirmation_message,
            config.discord_webhook_url
        )

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

def backfill(config: Config) -> None:
    # FMP per-symbol trade endpoints don't accept a date filter, so backfill
    # just fetches whatever is currently available and marks it seen.
    logger = logging.getLogger(__name__)
    logger.info("Starting backfill (fetching current data)")

    run_scan(config, send_alerts=False)

def main():
    parser = argparse.ArgumentParser(description="Congressional Trade Watcher")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("run", help="Perform one normal daily scan")
    subparsers.add_parser("test-alert", help="Send a sample Discord alert")
    subparsers.add_parser("backfill", help="Fetch data and populate seen_hashes without alerts")

    args = parser.parse_args()

    config = Config()
    setup_logging(config.log_level)

    if args.command == "run":
        run_scan(config)
    elif args.command == "test-alert":
        test_alert(config)
    elif args.command == "backfill":
        backfill(config)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()