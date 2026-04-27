# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Install: `pip install -r requirements.txt`

Run modes (CLI entrypoint is `src/main.py`):
- `python -m src.main run` — daily scan: fetch, dedupe, send Discord alerts
- `python -m src.main test-alert` — sends a sample Discord alert (uses a hard-coded record, not the API)
- `python -m src.main backfill` — fetches data and populates `data/seen_hashes.json` without sending alerts. Run before first production use to avoid alerting on historical disclosures. Internally calls `run_scan(send_alerts=False)`. (FMP per-symbol endpoints don't take a date filter, so there's no scope flag to pass.)

Tests (stdlib `unittest`, no pytest dep):
- All: `python -m unittest discover tests`
- Single file: `python -m unittest tests.test_dedupe`
- Single test: `python -m unittest tests.test_dedupe.TestDedupe.test_generate_fingerprint`

There is no linter or formatter configured.

## Configuration

`.env` (loaded via `python-dotenv` at import time in `src/config.py`):
- `FMP_API_KEY`, `DISCORD_WEBHOOK_URL` — required for `run`
- `LOG_LEVEL`, `REQUEST_TIMEOUT_SECONDS`, `MAX_RETRIES` — note that `MAX_RETRIES` counts *extra* attempts after the initial request (so `MAX_RETRIES=3` → up to 4 total attempts per FMP call). Internally exposed as `FMPClient.extra_retries`.
- `SEND_DISCLOSURE_ALERTS` (default `true`) — gates the per-disclosure Discord alerts in `run` mode.
- `SEND_CONFIRMATION_ALERT` (default `false`) and `CONFIRMATION_MESSAGE` — controls the "no new disclosures" end-of-run Discord ping; message supports `{total_fetched}` and `{new_records}` placeholders.

`config/watchlist.json` is a flat JSON array of ticker strings. `Config.load_watchlist()` uppercases, strips, and dedupes via `set()` — **order is not preserved**.

CI: `.github/workflows/main.yml` runs the daily scan at 13:00 UTC on Python 3.11. It synthesizes `.env` from `FMP_API_KEY` and `DISCORD_WEBHOOK_URL` repo secrets.

## Architecture

Linear pipeline driven by `src/main.py::run_scan`:

```
watchlist.json → FMPClient (per-symbol Senate + House fetch)
              → normalize_records (raw dict → NormalizedTradeRecord TypedDict)
              → dedupe.is_new_record (SHA256 fingerprint lookup)
              → alerts.alert_new_record (Discord webhook)
              → Storage.save_seen_hashes / save_last_run
```

Key invariants and gotchas:

- **Fingerprint fields** (`src/dedupe.py::_FINGERPRINT_FIELDS`) are: `source_chamber, symbol, politician_name, transaction_type, transaction_date, disclosure_date, amount_range, owner`. Changing this tuple invalidates every entry in `data/seen_hashes.json`. Encoding is JSON canonical (`json.dumps(..., separators=(",",":"))`) hashed with SHA-256. A legacy `|`-joined fingerprint is also computed in `is_new_record` so seen-hash entries written by older versions still suppress alerts; new entries are written under the JSON scheme only. The normalized values for `transaction_type` and `owner` are part of the fingerprint, so changing the canonical strings in `src/normalize.py` invalidates entries the same way.

- **`add_to_seen` is gated on alert delivery in run mode.** [src/main.py](src/main.py) only marks a new record seen after `alert_new_record` returns `True` (Discord post succeeded, or there's no webhook to deliver to). A failed Discord post leaves the record unseen so the next run retries — duplicate alert beats missed alert. Backfill mode (`send_alerts=False`) marks seen unconditionally, which is its purpose. Already-seen records get a no-op `add_to_seen` to keep them seen.

- **State files live under `data/`** (`seen_hashes.json`, `last_run.json`) and are written atomically via temp file + rename in `Storage.save_json`. `data/` is created on demand. `logs/app.log` is created by `setup_logging` before any logging happens.

- **Rate limiting is a hard `time.sleep(1)` before each API call** in `FMPClient` plus exponential backoff (`2 ** attempt`) on retries. With a watchlist of N symbols this is ~2N seconds of sleeping per run — keep this in mind when adding symbols or parallelism.

- **Per-symbol exception isolation**: a failure on one symbol logs and continues to the next; the run as a whole only fails for unrecoverable errors. Failed symbols silently miss their alerts for that run.

- **`NormalizedTradeRecord`** (`src/models.py`) is a `TypedDict` with `Literal` constraints on `source_chamber`, `transaction_type`, and `owner`. `normalize.py` is responsible for coercing arbitrary FMP field shapes into these literals — anything not matching becomes `"Other"` / `"Unknown"`.

- **End-of-run confirmation alert** only fires when `new_records == 0` and `SEND_CONFIRMATION_ALERT` is truthy. Runs that produced new alerts skip it (the per-disclosure alerts are themselves the proof-of-life).

## Notification triggers and how to suppress them

There are exactly two paths that post to Discord during a `run`:

| # | Trigger | Function | Fires when | Default | Suppress with |
|---|---------|----------|------------|---------|---------------|
| 1 | Per new disclosure | `alerts.alert_new_record` → `send_discord_alert` ([src/main.py:55-56](src/main.py:55)) | Record's fingerprint is not in `seen_hashes` and `SEND_DISCLOSURE_ALERTS` truthy | **on** (`SEND_DISCLOSURE_ALERTS=true`) | `SEND_DISCLOSURE_ALERTS=false`, `backfill`, or unset `DISCORD_WEBHOOK_URL` |
| 2 | End-of-run confirmation (proof-of-life) | `alerts.send_run_confirmation` ([src/main.py:73-79](src/main.py:73)) | Run completes with `new_records == 0` and `SEND_CONFIRMATION_ALERT` truthy | **off** (`SEND_CONFIRMATION_ALERT=false`) | leave default, `backfill`, or unset `DISCORD_WEBHOOK_URL` |

Each trigger has its own env var and is fully independent: flip either without affecting the other. `backfill` mode and an empty `DISCORD_WEBHOOK_URL` both still kill *both* triggers as a global override.

## Verifying tippee end-to-end

The tool is silent on a clean run with no new disclosures, so verification is its own concern:

- **Run on demand from CI:** `gh workflow run "Daily Congressional Trade Watch"` then `gh run watch`. The Actions UI shows green/red, and the run logs include the line `Run complete: fetched X records, Y new`.
- **Discord proof-of-life:** flip `SEND_CONFIRMATION_ALERT=true` (off by default). Every run with no new data then posts the `CONFIRMATION_MESSAGE`, so silence on Discord means the workflow didn't run at all.
- **Webhook reachability only:** `python -m src.main test-alert` posts a synthetic record with no API call.

## Interaction modes

- `/caveman` — talk like a caveman until told otherwise.

## Documentation map

- [docs/MANUAL.md](docs/MANUAL.md) — detailed setup/usage
- [docs/DECISIONS.md](docs/DECISIONS.md) — architectural rationale
- [docs/PLANS.md](docs/PLANS.md) — roadmap
- [src/scheduler_notes.md](src/scheduler_notes.md) — cron details
