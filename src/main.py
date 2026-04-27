import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
from .config import Config
from .storage import Storage
from .client import FMPClient
from .normalize import normalize_records
from .dedupe import is_new_record, add_to_seen
from .alerts import alert_new_record, send_run_confirmation
from .models import NormalizedTradeRecord

_LOGS_DIR = Path(__file__).resolve().parent.parent / "logs"


def setup_logging(log_level: str):
    level = getattr(logging, log_level.upper(), None)
    if not isinstance(level, int):
        raise ValueError(
            f"Invalid LOG_LEVEL={log_level!r}; expected one of: "
            "DEBUG, INFO, WARNING, ERROR, CRITICAL"
        )
    _LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(_LOGS_DIR / "app.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
        # Override any handlers a previous import (or test runner) may have
        # attached; otherwise basicConfig is a silent no-op.
        force=True,
    )


def _save_last_run(total_fetched: int, new_records: int, total_dropped: int = 0,
                   failed_fetches: int = 0, error: str | None = None) -> None:
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "fetched_records": total_fetched,
        "new_records": new_records,
        "dropped_records": total_dropped,
        "failed_fetches": failed_fetches,
    }
    if error:
        payload["error"] = error
    Storage.save_last_run(payload)


def run_scan(config: Config, send_alerts: bool = True) -> None:
    logger = logging.getLogger(__name__)
    logger.info("Starting run")

    # Validate FMP credentials up-front so misconfiguration surfaces clearly
    # instead of as 32 silent 403s with empty fetched_records.
    if not config.fmp_api_key:
        raise ValueError(
            "FMP_API_KEY is empty. Set it in .env or as an environment variable."
        )
    if send_alerts and config.send_disclosure_alerts and not config.discord_webhook_url:
        raise ValueError(
            "DISCORD_WEBHOOK_URL is empty but SEND_DISCLOSURE_ALERTS is true. "
            "Set the webhook or set SEND_DISCLOSURE_ALERTS=false to silence alerts."
        )

    watchlist = config.load_watchlist()
    if not watchlist:
        # Surface the empty-watchlist case so a truncated config doesn't
        # silently produce successful "0 alerts" runs forever.
        logger.warning("No symbols in watchlist (config/watchlist.json empty or missing)")
        _save_last_run(0, 0, error="empty watchlist")
        if send_alerts and config.send_confirmation_alert:
            send_run_confirmation(
                0, 0,
                "Congressional trade watcher run complete. Watchlist is empty — no symbols to scan.",
                config.discord_webhook_url,
            )
        return

    seen_hashes = Storage.load_seen_hashes()
    new_records = []
    total_fetched = 0
    total_dropped = 0
    failed_fetches = 0
    delivered_any = False

    with FMPClient(config.fmp_api_key, config.request_timeout_seconds, config.max_retries) as client:
        for symbol in watchlist:
            senate_data = []
            house_data = []
            try:
                senate_data = client.get_senate_trades(symbol)
            except Exception as e:
                logger.error(f"Failed to fetch senate trades for {symbol}: {e}")
                failed_fetches += 1
            try:
                house_data = client.get_house_trades(symbol)
            except Exception as e:
                logger.error(f"Failed to fetch house trades for {symbol}: {e}")
                failed_fetches += 1

            senate_records, senate_dropped = normalize_records(senate_data, "senate")
            house_records, house_dropped = normalize_records(house_data, "house")
            all_records = senate_records + house_records
            total_fetched += len(all_records)
            total_dropped += senate_dropped + house_dropped
            if senate_dropped or house_dropped:
                logger.info(
                    "%s: dropped %d senate / %d house records during normalize",
                    symbol, senate_dropped, house_dropped,
                )

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
                        delivered_any = True
                else:
                    add_to_seen(record, seen_hashes)  # idempotent; keeps already-seen records seen

    Storage.save_seen_hashes(seen_hashes)
    _save_last_run(total_fetched, len(new_records), total_dropped, failed_fetches)

    logger.info(
        "Run complete: fetched %d records (%d dropped during normalize), "
        "%d new, %d chamber-fetches failed",
        total_fetched, total_dropped, len(new_records), failed_fetches,
    )

    # Confirmation gate keys off "delivered_any", not "any new records detected" —
    # otherwise SEND_DISCLOSURE_ALERTS=false silences the heartbeat too whenever
    # records arrive (the user's only Discord output goes missing).
    if send_alerts and config.send_confirmation_alert and not delivered_any:
        send_run_confirmation(
            total_fetched,
            len(new_records),
            config.confirmation_message,
            config.discord_webhook_url,
        )


def test_alert(config: Config) -> int:
    """Returns process exit code (0 success, non-zero on Discord failure)."""
    logger = logging.getLogger(__name__)
    logger.info("Sending test alert")

    if not config.discord_webhook_url:
        logger.error("DISCORD_WEBHOOK_URL is empty — nothing to test against. Set it in .env.")
        return 2

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

    return 0 if alert_new_record(sample, config.discord_webhook_url) else 1


def backfill(config: Config) -> None:
    # FMP per-symbol trade endpoints don't accept a date filter, so backfill
    # just fetches whatever is currently available and marks it seen.
    logger = logging.getLogger(__name__)
    logger.info("Starting backfill (fetching current data)")

    run_scan(config, send_alerts=False)


def main():
    # Load .env at CLI entry (not at config import time) so tests can construct
    # Config() in isolation.
    load_dotenv()

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
        sys.exit(test_alert(config))
    elif args.command == "backfill":
        backfill(config)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
