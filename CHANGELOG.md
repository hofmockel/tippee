# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Removed
- `--days` flag from the `backfill` subcommand. The flag was accepted and logged but never affected behavior because the FMP per-symbol trade endpoints don't accept a date filter — `backfill --days 1` and `backfill --days 365` did the same thing. The command is now just `python -m src.main backfill`. README, INSTALL.md, docs/MANUAL.md, src/scheduler_notes.md, and CLAUDE.md updated accordingly.

### Security
- Stopped logging the FMP API key. Previously, the URL passed to `_get_with_retries` included `?apikey=<secret>` in the query string, and any non-2xx response wrote the full URL to `logs/app.log` and stdout (which CI captures). The client now passes credentials via `httpx`'s `params=` kwarg so the logged URL contains only the path. Rotate any FMP key whose value may have appeared in historical logs.

### Fixed
- `SEND_DISCLOSURE_ALERTS=false` no longer permanently skips disclosures. Previously, disabling the toggle still wrote new records' fingerprints to `data/seen_hashes.json`, so re-enabling later would never re-deliver them. The toggle now suppresses both the Discord alert and the seen-hash write, so any disclosures that arrive while it's off will be alerted on the next run with the toggle back on. Backfill mode (`send_alerts=False`) is unchanged — it still seeds seen hashes as designed.
- Failed Discord posts no longer mark records as seen. `send_discord_alert` now propagates a success bool through `alert_new_record`, and `run_scan` only calls `add_to_seen` when delivery succeeds. A Discord 5xx, timeout, or any other webhook failure leaves the record unseen so the next run retries — duplicate alert beats missed alert.
- Per-chamber fetch failures are now isolated. Previously, a `senate_data` fetch could succeed and then a `house_data` fetch could throw, sending the entire symbol's already-fetched senate disclosures into the per-symbol exception handler with no alerts fired. Each chamber now has its own try block, and processing continues with whichever side returned data.
- Discord rate-limit (HTTP 429) responses are now retried up to 3 times, honouring the `Retry-After` header (capped at 60 s). Previously a single 429 dropped the alert.
- `FMPClient` is now a context manager and closes its underlying `httpx.Client`. Used as `with FMPClient(...) as client:` in `run_scan`. Eliminates the `ResourceWarning` and the file-descriptor leak on long-lived imports.
- Watchlist load order is now deterministic. `Config.load_watchlist` deduplicates with `dict.fromkeys` instead of `set`, so symbols are fetched in the order they appear in `config/watchlist.json` on every run.
- `config/watchlist.json` is now resolved relative to the project root (one level above `src/`) instead of the current working directory. The CLI no longer silently returns an empty watchlist when launched from a different cwd.
- `Storage.save_json` now removes its `.tmp` file when serialization or rename fails. Previously a non-serializable value would leave orphan `tmp*.tmp` files accumulating in `data/` and `logs/` parents.
- Dedupe fingerprint switched from `|`-joined to JSON canonical encoding (`json.dumps(..., separators=(",",":"))`) so a literal `|` in any field can no longer collide two different records. Existing `data/seen_hashes.json` entries written under the old scheme are still honoured via a legacy-fingerprint fallback in `is_new_record`, so no re-flood of alerts on first run after upgrade. New records are written under the new scheme only; legacy entries become inert over time.
- `last_run.json` timestamp is now written in UTC with an explicit offset (`datetime.now(timezone.utc).isoformat()`) instead of a naive local-time string. Timestamps are now comparable across hosts (CI is UTC, dev laptops vary).

### Changed
- Defaulted `SEND_CONFIRMATION_ALERT` to `false`, so runs only send alerts when there is a new disclosure to report.
- Added documentation for toggling heartbeat/confirmation behavior with `SEND_CONFIRMATION_ALERT` and `CONFIRMATION_MESSAGE`.
- Updated local cron examples to run at 9:27 AM America/New_York on weekdays (3 minutes before U.S. market open).
- Updated GitHub Actions schedule to `27 13 * * 1-5` (UTC weekdays).


## [1.0.1] - 2026-04-23

### Added
- python-dotenv support for loading .env configuration files
- REQUIREMENTS.md documentation
- Comprehensive markdown documentation suite
- agents.md for tracking AI agents and knowledge base

### Changed
- Updated config.py to automatically load environment variables from .env
- Enhanced documentation structure with full project guides
- Added default symbol watchlist (15 tech/semiconductor stocks)

### Fixed
- Application now properly reads .env file with API credentials

## [1.0.0] - 2026-04-23

### Added
- Initial implementation of Congressional Trade Watcher
- Support for monitoring Senate and House trade disclosures via FMP API
- Discord webhook alerts for new disclosures
- SHA-256 fingerprint-based deduplication
- Three CLI commands: run, test-alert, backfill
- Comprehensive documentation and user manual
- Unit tests for normalization and deduplication
- Cron scheduling support
- Exponential backoff retry logic
- Structured logging to console and file

### Technical Stack
- Python 3.11+
- Minimal dependencies: httpx, python-dotenv
- Local JSON storage for persistence
- Financial Modeling Prep API integration
- No database required

## [1.0.0] - 2026-04-23

### Added
- Complete system implementation
- Documentation suite
- Test coverage
- Open source licensing (MIT)
