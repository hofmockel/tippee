# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Removed
- `--days` flag from the `backfill` subcommand. The flag was accepted and logged but never affected behavior because the FMP per-symbol trade endpoints don't accept a date filter — `backfill --days 1` and `backfill --days 365` did the same thing. The command is now just `python -m src.main backfill`. README, INSTALL.md, docs/MANUAL.md, src/scheduler_notes.md, and CLAUDE.md updated accordingly.

### Security
- Stopped logging the FMP API key. Previously, the URL passed to `_get_with_retries` included `?apikey=<secret>` in the query string, and any non-2xx response wrote the full URL to `logs/app.log` and stdout (which CI captures). The client now passes credentials via `httpx`'s `params=` kwarg so the logged URL contains only the path. Rotate any FMP key whose value may have appeared in historical logs.

### Added
- `last_run.json` now records `dropped_records` (count of records `normalize_records` couldn't parse) and `failed_fetches` (count of per-chamber HTTP fetches that raised), surfacing previously-silent data loss. The run-complete log line includes them too.
- GitHub Actions workflow now persists `data/` between runs via `actions/cache/restore` + `actions/cache/save` with a rolling key. Previously, every cron run started on a fresh runner with an empty `seen_hashes` set and re-alerted on every historical disclosure FMP returned. The save step uses `if: always()` so a partially-updated state file is preserved even on failure. **Fixes the highest-severity bug in the project**; if the workflow has been deployed and re-flooding Discord, this stops it.

### Fixed
- Removed fragile `"403" in str(e)` substring match in `_get_with_retries`'s non-status `httpx.HTTPError` branch. Real 403s carry a status code and are caught earlier; the substring check fired false positives on transport errors that happened to contain `"403"` (e.g., port `4030` in a connection-refused message), turning a retryable network blip into a hard failure. Updated the corresponding test to assert that a non-status error containing `"403"` now retries instead of failing fast.
- `Storage.load_seen_hashes` now validates the `hashes` value is a list before calling `set()` on it. Previously, a `{"hashes": "abc"}` shape (string instead of list) would silently produce three single-character "fingerprints" that match nothing, re-flooding alerts with no warning. Non-list values are now logged as an error and treated as empty; non-string entries inside the list are filtered out.
- `(raw.get(x, raw.get(y, ...)))` fallback patterns in `normalize_record` now correctly fall through when the first key is present-and-`None`. Previously a `{"transactionType": null, "type": "Purchase"}` response would lose the `"Purchase"` value because `dict.get(k, default)` returns the explicit `None`, never reaching `default`. (Already fixed incidentally as part of the prior batch's None-coercion work; backlog entry was carried forward and is now retired.)
- `send_run_confirmation` now uses the same `_post_to_discord` helper as `send_discord_alert`, getting 429-with-Retry-After and 5xx-with-exponential-backoff retry handling. Previously, the heartbeat ping was a single bare POST that dropped on the exact burst pattern (many alerts followed by a heartbeat) most likely to trip Discord's rate limit.
- `_legacy_fingerprint` now coerces `None` / non-string fields to empty strings before joining, so the legacy fallback can no longer crash dedupe via `TypeError: sequence item N: expected str instance, NoneType found`. The newer JSON-based `generate_fingerprint` already handled this; the legacy path had quietly regressed.
- `Storage.save_json` now accepts an `indent` keyword (default `2` to preserve `last_run.json`'s human-readable format). `save_seen_hashes` passes `indent=None` so `seen_hashes.json` is written compact — sensible for a file of thousands of opaque SHA-256 hashes that no human reads, and important for any future commit-back persistence strategy.
- `MAX_RETRIES` semantics are now documented explicitly. The env var counts *extra* attempts after the initial request, so `MAX_RETRIES=3` means up to 4 total HTTP attempts. The internal `FMPClient` field is renamed `extra_retries` for code clarity; the public `max_retries` constructor arg name is unchanged for backward compat. `.env.example` and CLAUDE.md note the off-by-one explicitly.
- GitHub Actions workflow now has a `concurrency: { group: tippee-scan, cancel-in-progress: false }` block so cron + manual `workflow_dispatch` runs serialize instead of racing on the `tippee-state` cache. Without this, two parallel runs could restore the same starting `seen_hashes`, post overlapping Discord alerts, and last-writer-wins on the cache save.
- `logging.FileHandler` now pins `encoding="utf-8"`. Previously, on hosts where the platform default was anything else (Windows `cp1252`, minimal Linux containers with `LANG=C`), a Unicode character in any logged FMP response could raise `UnicodeEncodeError` from inside the logging machinery and crash the run mid-loop.
- Empty watchlist runs are no longer silent. `run_scan` now writes `last_run.json` with `error="empty watchlist"` and (if `SEND_CONFIRMATION_ALERT` is on) sends a Discord message saying the watchlist is empty. Previously, a truncated `config/watchlist.json` resulted in a single warning log line and zero observable signal — cron jobs could miss alerts for weeks before anyone noticed.
- `python -m src.main test-alert` now exits non-zero when the Discord post fails, and errors out with exit code 2 if `DISCORD_WEBHOOK_URL` is empty. Previously it always exited 0, making the documented "webhook smoke test" advice meaningless and disguising a missing webhook URL as a successful test.
- `run_scan` now validates `FMP_API_KEY` at startup (always required) and `DISCORD_WEBHOOK_URL` (required when `SEND_DISCLOSURE_ALERTS` is true), failing fast with a clear message that names the env var. Previously, an empty key produced 32 silent 403s per run and a `fetched_records=0` summary that looked successful. `test-alert` does its own webhook check (above), so users who only want to test their webhook don't need an FMP key.
- `LOG_LEVEL=<typo>` now raises a named ValueError listing valid level names, instead of an opaque `AttributeError: module 'logging' has no attribute 'DEBG'`.
- `SEND_CONFIRMATION_ALERT` now fires whenever no records were *delivered to Discord*, not whenever no records were *detected*. Previously, the combination `SEND_DISCLOSURE_ALERTS=false` + `SEND_CONFIRMATION_ALERT=true` resulted in zero Discord output on runs that detected new disclosures (records were silenced but counted, suppressing the heartbeat). The user wanting "heartbeat as my only Discord output" now actually gets it.
- `FMPClient` now treats HTTP 200 with a non-list JSON body (e.g., `{"Error Message": "Invalid API KEY"}`) as a per-symbol failure: logs the error message (without the API key) and returns an empty list for that fetch so the run continues. Previously, the dict would propagate to `normalize_records`, which iterated dict keys as records and produced a wall of "Error normalizing record" warnings.
- `normalize_date` now parses ISO 8601 with time (e.g., `"2026-04-01T00:00:00.000Z"`) via `datetime.fromisoformat`. The legacy three-format list is the fallback. Previously, ISO inputs passed through unparsed and entered the dedupe fingerprint with their full timestamp — so any FMP reformatting (e.g., dropping milliseconds) re-alerted everything.
- `normalize_records` now returns `(records, dropped_count)` instead of just `records`. `run_scan` aggregates the count, logs per-symbol drops at INFO, and includes the total in `last_run.json` and the run-complete log line. Previously, if FMP returned 100 records and 99 failed to normalize, the run summary said "1 record" with no signal of the silent loss.
- `load_dotenv()` is now called from `main()` at CLI entry, not at `src.config` module import. Tests that construct `Config()` after patching `os.environ` now see their patches take effect, instead of being defeated by the `.env` loading that previously happened the moment anything imported the package.
- `Storage.load_json` and `Storage.save_json` now pin `encoding="utf-8"`. Previously, runs on hosts with a non-UTF-8 locale (Windows `cp1252`, minimal Linux containers with `LANG=C`) could crash on Unicode in normalized fields — accented politician names, em-dashes in issuer descriptions.
- Per-symbol fetch failures are now surfaced in the run-complete log line and `last_run.json` (via `failed_fetches`). Previously, a chamber-fetch exception was logged once and then absorbed into the totals; the user saw `Run complete: fetched 47 records, 2 new` with no signal that 5 of 32 chamber-fetches had failed. (Fixed as a side effect of the `dropped_records` work above.)
- Discord 5xx responses are now retried with exponential backoff (capped at 60 s), matching the existing 429 handling. Previously, a single Discord 502/503 would drop the alert; combined with the gated `add_to_seen`, that meant the next retry attempt was the *next scheduled cron run* (potentially 24 h away). 4xx responses other than 429 still fail-fast.
- `Storage.load_json` no longer crashes the whole run on a corrupt or unreadable state file. `JSONDecodeError` and `OSError` are caught, logged with the file path, and treated as empty. Dedupe degrades gracefully to "alert spam" — recoverable — instead of crashing — not recoverable.
- `logs/` and `data/` directories are now anchored to the project root (`Path(__file__).resolve().parent.parent`) instead of the current working directory. Mirrors the prior watchlist-path fix; closes the gap for the other two on-disk locations. Cron jobs that don't `cd` first no longer scatter stray `logs/` and `data/` directories around the filesystem.
- `setup_logging` now passes `force=True` to `logging.basicConfig`, so log level/format/handlers apply even when the root logger already has handlers attached (e.g., from a test runner or an upstream import). Previously, `basicConfig` was a silent no-op in those scenarios and `logs/app.log` could stay empty.
- Numeric env vars (`REQUEST_TIMEOUT_SECONDS`, `MAX_RETRIES`) now fail fast with a named error: `Invalid REQUEST_TIMEOUT_SECONDS='abc'; expected an integer` instead of an opaque `ValueError` from inside Python's int parser. `MAX_RETRIES` is also validated to be `>= 0`, and `REQUEST_TIMEOUT_SECONDS` to be `>= 1`.
- `FMPClient._get_with_retries` no longer has a reachable `return []` at the end. With negative `MAX_RETRIES` rejected at config-validation time (above), the loop always runs at least once, so the trailing line is replaced with `raise RuntimeError(...)` — defense in depth against the dead-code-becomes-live failure mode where a misconfigured retry count silently swallowed every symbol's data.
- `normalize_transaction_type`, `normalize_owner`, and the field-extraction in `normalize_record` now coerce `None` to empty string (`(value or "").lower()`, `raw.get(...) or raw.get(...) or ""`) instead of raising AttributeError when FMP returns explicit nulls. The error path no longer dumps the entire raw record into logs — it logs just the symbol or politician name as a redacted identifier, preventing PII / free-text issuer descriptions from landing in CI artifacts.
- `normalize_record` now drops records with empty `transaction_date` or `disclosure_date`. Previously, two genuinely different disclosures with missing dates produced identical fingerprints (since `""|""|"..."` collapses), causing dedupe collisions. Records without dates are skipped with a one-line warning naming the symbol and politician.
- `Storage.save_seen_hashes` now writes the hash list `sorted()` instead of via `list(set(...))`. The file is byte-stable across runs whose hash set didn't change — important for diff-based persistence strategies (a follow-on to the workflow caching above) and for diff-readability in general.
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
