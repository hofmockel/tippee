# Backlog

Twenty bugs total — first 10 from the previous scan, ten more from this one. Roughly ordered by severity within each batch.

## Bugs (batch 1)

### 1. CI re-alerts on every historical disclosure on every scheduled run

**Where:** [.github/workflows/main.yml](.github/workflows/main.yml) — and by implication, the missing cache/artifact step

The workflow runs on a fresh `ubuntu-latest` runner each invocation. `data/seen_hashes.json` lives on that ephemeral filesystem and is **never persisted** — no `actions/cache`, no `actions/upload-artifact` + `download-artifact`, no commit-back step. Every cron run starts with an empty `seen_hashes` set, so every disclosure FMP returns is treated as new and posted to Discord. With 16 watchlist symbols × Senate+House × historical depth, this is potentially dozens of duplicate alerts per weekday.

The dedupe code, the legacy-fingerprint fallback, and even the SEND_DISCLOSURE_ALERTS toggle are all defeated by this — they're working correctly on a state file that doesn't exist.

**Impact:** This is the highest-severity bug in the project. Either (a) the workflow has been deployed and is silently spamming Discord (in which case the user has presumably noticed), or (b) it hasn't been deployed yet and the first cron firing will flood. Either way it's load-bearing.

**Fix:** add an `actions/cache@v4` step keyed on something stable (e.g., the workflow file path) that restores/saves `data/`. Or upload `data/seen_hashes.json` as an artifact and download the latest from the previous run. Or run `git commit && git push` of the data file at the end of the workflow (uglier — needs a deploy key or PAT).

---

### 2. Discord 5xx responses are not retried — alerts dropped on transient outages

**Where:** [src/alerts.py:54-69](src/alerts.py:54)

```python
for attempt in range(_MAX_DISCORD_RETRIES):
    try:
        response = httpx.post(webhook_url, json=payload, timeout=10)
        if response.status_code == 429:
            ...
            continue
        response.raise_for_status()    # 5xx → HTTPStatusError → except → return False
        ...
    except Exception as e:
        logger.error(f"Failed to send Discord alert: {e}")
        return False
```

The 429 path retries with backoff (Bug 4 from the previous batch), but every other non-2xx — including transient 502/503 from Discord — falls into `raise_for_status()` and immediately returns False. Discord's own docs recommend retrying 5xx with backoff. Combined with the gated `add_to_seen` (good!), this means Discord 5xx leaves the record unseen, so the next run retries — but only the *next scheduled run*, which could be 24 hours away.

**Fix:** treat 5xx the same as 429: retry up to `_MAX_DISCORD_RETRIES` with exponential backoff (e.g., `2 ** attempt` seconds). Distinguish from 4xx (other than 429), which should still fail-fast since they indicate caller error.

---

### 3. `Storage.load_json` crashes the whole run on a corrupt state file

**Where:** [src/storage.py:7-12](src/storage.py:7)

```python
@staticmethod
def load_json(file_path: Path) -> Dict[str, Any]:
    if not file_path.exists():
        return {}
    with open(file_path, "r") as f:
        return json.load(f)
```

If `data/seen_hashes.json` is truncated, contains invalid JSON, or was partially written by a pre-Bug-8-fix version, `json.load` raises `JSONDecodeError`, which propagates up through `Storage.load_seen_hashes` → `run_scan` → `main()` and aborts the entire run. The user gets a stack trace, no alerts, and the next scheduled run hits the same crash.

**Fix:** catch `JSONDecodeError` (and `OSError`) in `load_json`, log a clear error pointing at the file, and return `{}`. Optionally rename the bad file to `<name>.corrupt-<timestamp>` so the user can inspect it. The downside — treating a corrupt seen_hashes as empty — is alert spam, but that's recoverable; a permanent crash is not.

---

### 4. `logs/` directory created relative to CWD

**Where:** [src/main.py:15](src/main.py:15)

```python
def setup_logging(log_level: str):
    Path("logs").mkdir(parents=True, exist_ok=True)
    ...
    logging.FileHandler("logs/app.log"),
```

Same root cause as the previously-fixed watchlist path bug (#7 in the prior batch). `Path("logs")` resolves against the current working directory, so launching the CLI from anywhere other than the repo root creates a stray `logs/` next to the user. The `data/` directory has the same problem (created on demand by `Storage.save_json` via `file_path.parent.mkdir`, where `file_path` is also a relative `Path("data/seen_hashes.json")`).

**Fix:** define a `_PROJECT_ROOT = Path(__file__).resolve().parent.parent` constant in a shared module, and resolve `logs/`, `data/seen_hashes.json`, `data/last_run.json`, and the watchlist against it. Currently the watchlist is the only path that does this.

---

### 5. `logging.basicConfig` is a no-op if any handler is already configured

**Where:** [src/main.py:14-23](src/main.py:14)

```python
def setup_logging(log_level: str):
    Path("logs").mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="...",
        handlers=[FileHandler(...), StreamHandler(...)],
    )
```

Per the stdlib docs, `basicConfig` does nothing if the root logger already has handlers — which happens if anything earlier (a dependency, a test runner, a notebook) configured logging. The result is silently wrong: log level isn't honoured, our file/stream handlers aren't attached, and `logs/app.log` may stay empty.

**Fix:** either use `force=True` (Python 3.8+) to override existing config, or set up the root logger explicitly: `root = logging.getLogger(); root.setLevel(...); root.handlers = [...]`. The `force=True` form is one line.

---

### 6. Numeric env vars crash at startup on non-numeric input

**Where:** [src/config.py:15-16](src/config.py:15)

```python
self.request_timeout_seconds = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "20"))
self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
```

A typo or accidentally-quoted value in `.env` (e.g., `MAX_RETRIES="three"`) raises `ValueError` at `Config()` construction time, which is before `setup_logging` runs, so the user gets an unconfigured stack trace with no log file. The error message names Python internals, not the env var that caused it.

**Fix:** wrap the parses in a helper that catches ValueError and either falls back to the default with a clear warning, or fails with a user-friendly error message naming the offending env var: `Invalid REQUEST_TIMEOUT_SECONDS=<value>; expected an integer`.

---

### 7. Negative `MAX_RETRIES` makes `_get_with_retries` silently return `[]`

**Where:** [src/client.py:81-82](src/client.py:81), [src/client.py:33](src/client.py:33)

```python
for attempt in range(self.max_retries + 1):
    ...
return []   # was dead code; reachable when max_retries < 0
```

If `MAX_RETRIES=-1`, `range(0)` yields zero iterations, the function falls through to `return []`, and the caller sees an empty record list — same as a successful API call that returned no trades. No exception, no log, no alert. The symbol is silently skipped on every run as long as the env var stays misconfigured.

**Fix:** validate in `Config` that `max_retries >= 0` (and probably `request_timeout_seconds > 0`), raising a clear error otherwise. Or in `FMPClient.__init__`, clamp to `max(0, max_retries)`. The `return []` line should also become `raise RuntimeError("unreachable")` so the dead-code-becomes-live failure mode can never recur.

---

### 8. `normalize_transaction_type` / `normalize_owner` raise AttributeError on `None`; the entire raw record is logged

**Where:** [src/normalize.py:25-49](src/normalize.py:25), [src/normalize.py:51-83](src/normalize.py:51)

```python
def normalize_transaction_type(tx_type: str) -> str:
    tx_type = tx_type.lower()    # AttributeError if tx_type is None
    ...

# In normalize_record:
transaction_type = normalize_transaction_type(raw.get("transactionType", raw.get("type", "")))
```

If FMP returns `{"transactionType": null, ...}`, `raw.get("transactionType", "")` returns `None` (not `""`, because the key exists). `normalize_transaction_type(None)` raises AttributeError, caught by the outer try in `normalize_record`, which logs `f"Error normalizing record: {e}, raw: {raw}"` — dumping the entire raw dict into `logs/app.log` and stdout. Two problems:

- The record is silently dropped — no alert, no count of how many were dropped.
- The full raw record (which can include politician PII, free-text issuer descriptions, FMP internal IDs) is committed to logs that may end up in CI artifacts.

Same shape applies to `normalize_owner(None)` and `raw.get("symbol", "").upper()` if `symbol` is None.

**Fix:** coerce `None` → `""` at the helper boundary (`tx_type = (tx_type or "").lower()`). For the outer try, log just the field that failed and a fingerprint-safe identifier, not the whole `raw` dict.

---

### 9. Records with missing dates collide in the dedupe fingerprint

**Where:** [src/normalize.py:69-71](src/normalize.py:69), [src/dedupe.py](src/dedupe.py)

`normalize_record` only requires `symbol` and `politician_name` to be non-empty. `transaction_date` and `disclosure_date` can be `""` (when FMP omits them, or when `normalize_date` fails to parse all three formats and returns the input — which can be `""`).

Two genuinely different disclosures from the same politician on the same symbol with the same amount and owner — but missing dates — produce identical fingerprints (`source_chamber|symbol|politician|type||||owner`-equivalent), and only the first one alerts. Empirically rare but real.

**Fix:** drop records with empty `transaction_date` or `disclosure_date` in `normalize_record` (same as the missing-symbol guard) — better to miss the record than to silently dedupe it against an unrelated one. Optionally include the index from `raw_record` (e.g., FMP's internal `id`) in the fingerprint as a tiebreaker for records that are otherwise identical.

---

### 10. `data/seen_hashes.json` content order is non-deterministic

**Where:** [src/storage.py:30-32](src/storage.py:30)

```python
@staticmethod
def save_seen_hashes(hashes: Set[str]) -> None:
    data = {"hashes": list(hashes)}
    Storage.save_json(Path("data/seen_hashes.json"), data)
```

`list(set)` ordering is hash-randomized per Python process. Every save writes the hashes in a different order, so anyone diffing the file (or committing it to git as a workaround for Bug 1 above) sees noise on every run even when the *set* of hashes is unchanged. Cosmetic but it would make a "commit-back" persistence strategy untenable.

**Fix:** `data = {"hashes": sorted(hashes)}` — costs an O(n log n) sort on a few thousand strings, totally negligible, and the file becomes byte-identical across runs whose `seen_hashes` set didn't change. Useful regardless of how Bug 1 is ultimately solved.

---

## Bugs (batch 2)

### 11. Empty watchlist exits silently — no state save, no Discord ping, no signal anything ran

**Where:** [src/main.py:30-32](src/main.py:30)

```python
watchlist = config.load_watchlist()
if not watchlist:
    logger.warning("No symbols in watchlist")
    return
```

When `config/watchlist.json` is empty, malformed, or missing entirely (the file-missing case was made more likely by a previous bug we already fixed in this area), `run_scan` returns immediately. `last_run.json` is *not* updated, no confirmation alert fires (`send_confirmation_alert` is gated behind the early-return), and the only signal is one warning line in `logs/app.log`.

If the user's cron job is running daily but the watchlist accidentally got truncated, they have no Discord-side or `last_run.json`-side signal that anything is wrong. They notice when they expected an alert and didn't get one — possibly weeks later.

**Fix:** still write `last_run.json` with `fetched_records=0, new_records=0, error="no symbols"` even on early-return, and (if `SEND_CONFIRMATION_ALERT` is on) post a confirmation message that explicitly says the watchlist was empty. Or, more aggressively, treat an empty watchlist as a hard error (non-zero exit) so the GitHub Actions run goes red.

---

### 12. `test-alert` exit code is always 0 — useless as a webhook smoke test

**Where:** [src/main.py:104](src/main.py:104)

```python
def test_alert(config: Config) -> None:
    ...
    alert_new_record(sample, config.discord_webhook_url)   # bool return discarded
```

`alert_new_record` now returns a bool indicating Discord delivery success (one of the prior fixes). `test_alert` discards it and returns None, so `python -m src.main test-alert` exits 0 whether the webhook posted or 404'd or had no URL configured at all. This makes the documented "webhook smoke test" advice (in CLAUDE.md and README) hollow — the script lies about success.

Also: if `discord_webhook_url` is empty, `alert_new_record` returns True (no webhook to fail against), so `test-alert` claims success while having sent nothing to Discord. Worse than failing, since the user assumes the test passed.

**Fix:** in `test_alert`, require `config.discord_webhook_url` to be non-empty (error out with a clear message if not), and `sys.exit(0 if alert_new_record(...) else 1)`.

---

### 13. Required env vars (`FMP_API_KEY`, `DISCORD_WEBHOOK_URL`) not validated at startup

**Where:** [src/config.py:12-13](src/config.py:12)

```python
self.fmp_api_key = os.getenv("FMP_API_KEY", "")
self.discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "")
```

Both default to `""`. `Config()` succeeds. The first FMP call then sends `?apikey=` (empty), hits a 403, gets non-retried (403 isn't in the retryable set) — the symbol's senate fetch fails, the symbol's house fetch fails, the loop continues, the run completes "successfully" with `fetched_records=0`. The user sees no alerts and a green CI run, with no clear pointer at "you forgot to set FMP_API_KEY."

Same shape applies to an empty `DISCORD_WEBHOOK_URL` — disclosure alerts silently fall through `alert_new_record`'s "no webhook" branch and return True, so records get marked seen with no Discord post.

**Fix:** in `Config.__init__`, fail fast with a clear message if `fmp_api_key` is empty (always required) and if `discord_webhook_url` is empty *and* `SEND_DISCLOSURE_ALERTS` is true (otherwise the user is intentionally silencing). Or surface "0 records fetched, 0 alerts sent — config may be incomplete" in the run summary.

---

### 14. `LOG_LEVEL=<typo>` crashes before logging is set up — opaque AttributeError

**Where:** [src/main.py:17](src/main.py:17)

```python
logging.basicConfig(
    level=getattr(logging, log_level.upper()),
    ...
)
```

If `LOG_LEVEL=DEBG` (typo) or `LOG_LEVEL=verbose` (custom), `getattr(logging, "DEBG")` raises `AttributeError: module 'logging' has no attribute 'DEBG'`. This happens *inside* `setup_logging`, before any handlers are attached, so the user sees a bare traceback on stderr with no log file written and no clear hint that the env var was the cause.

**Fix:** `level = getattr(logging, log_level.upper(), logging.INFO)` with a stderr warning if the lookup fell back. Or `if log_level.upper() not in logging._nameToLevel: raise ConfigError(...)` with a message naming the env var and the valid values.

---

### 15. `SEND_CONFIRMATION_ALERT` is suppressed when there were new records — even if those records' alerts were silenced

**Where:** [src/main.py:53-59, 78-84](src/main.py:53)

```python
for record in all_records:
    if is_new_record(record, seen_hashes):
        new_records.append(record)                 # always appended
        if send_alerts and not config.send_disclosure_alerts:
            continue                                # silenced, but counted as "new"
        ...
...
if send_alerts and len(new_records) == 0 and config.send_confirmation_alert:
    send_run_confirmation(...)                      # skipped because len(new_records) > 0
```

`new_records` is appended to *before* the `SEND_DISCLOSURE_ALERTS` gate. So if the user has `SEND_DISCLOSURE_ALERTS=false` (silencing per-disclosure alerts) *and* `SEND_CONFIRMATION_ALERT=true` (wanting the heartbeat as their only Discord output), and 5 new records arrive, the confirmation alert is suppressed because `len(new_records) == 5`. The user gets nothing — exactly the opposite of their intent.

**Fix:** the confirmation gate should check "no records were *actually delivered*", not "no records were detected." Either track delivered vs detected separately, or — simpler — change the gate to `if send_alerts and config.send_confirmation_alert and not delivered_any:`.

---

### 16. `_get_with_retries` doesn't validate JSON response shape

**Where:** [src/client.py:37-40](src/client.py:37)

```python
response = self.client.get(url, params=params)
response.raise_for_status()
return response.json()
```

FMP (like many APIs) sometimes returns HTTP 200 with an error body — e.g., `{"Error Message": "Invalid API KEY"}` or `{"error": "rate limit exceeded"}`. `raise_for_status` doesn't catch these, and `response.json()` returns the dict. That dict is passed to `normalize_records(raw_records, chamber)`, which iterates `for raw in raw_records` — iterating dict keys (strings) instead of records. Each "record" is then passed to `normalize_record(raw, chamber)`, which calls `raw.get(...)`, raising AttributeError → outer try → returns None. Net effect: silent zero-record fetch with a wall of "Error normalizing record" warnings.

**Fix:** in `_get_with_retries`, after `response.json()`, validate `isinstance(parsed, list)`. If not, log the body (with API key redacted) and raise — that's an unrecoverable API contract violation. Or, narrower: if the body is a dict with an `Error Message` / `error` key, treat it as a non-retryable failure.

---

### 17. `normalize_date` only handles 3 formats; ISO datetime (FMP's standard for some endpoints) silently passes through unparsed

**Where:** [src/normalize.py:8-23](src/normalize.py:8)

```python
for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y"]:
    try:
        dt = datetime.strptime(date_str, fmt)
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        continue
logger.warning(f"Could not parse date: {date_str}")
return date_str
```

If FMP returns `"2026-04-01T00:00:00.000Z"` (ISO 8601 with time, common across their API surface), none of the three formats match. `normalize_date` logs a warning and returns the original string. The fingerprint then includes the full ISO string with milliseconds — so re-fetching the same record after FMP's clock granularity changes (or them reformatting to e.g. `"2026-04-01T00:00:00Z"` without milliseconds) breaks dedupe and re-alerts everything.

**Fix:** add `"%Y-%m-%dT%H:%M:%S"` (with optional `.%fZ` handling) to the format list. Or just `datetime.fromisoformat(date_str.rstrip("Z")).date().isoformat()` as a first-try before the legacy formats. Strip everything to `YYYY-MM-DD` so day-of resolution is what feeds the fingerprint regardless of upstream format.

---

### 18. `normalize_records` silently drops failed records with no aggregate visibility

**Where:** [src/normalize.py:84-91](src/normalize.py:84)

```python
def normalize_records(raw_records, chamber):
    normalized = []
    for raw in raw_records:
        norm = normalize_record(raw, chamber)
        if norm:
            normalized.append(norm)
    return normalized
```

Each individual `normalize_record` failure is logged (often with the entire raw record — see batch-1 bug #8), but the *count* is never surfaced. If FMP returns 100 records and 99 fail to normalize, `run_scan` sees 1 record, posts 1 alert, and reports `Run complete: fetched 1 records, 1 new` — there's no signal that 99 records were silently dropped.

**Fix:** return both counts from `normalize_records` (e.g., `(records, dropped_count)`), and have `run_scan` log `"normalized X of Y senate records (Z dropped)"` after each chamber's fetch. Or accumulate a `dropped` counter and include it in `last_run.json` and the run-complete log line.

---

### 19. `load_dotenv()` runs at module import time — tests can't override env after import

**Where:** [src/config.py:8](src/config.py:8)

```python
# Load .env file
load_dotenv()
```

The call sits at module top level. As soon as anything imports `src.config` (which is everything via `src.main`), the `.env` file is read into the process environment. Tests that try to do:

```python
os.environ["MAX_RETRIES"] = "5"
from src.config import Config
config = Config()   # might still see the .env value
```

…can be defeated by the fact that `.env` was already loaded before the test's `os.environ` patch took effect, and `load_dotenv` defaults to *not* overriding existing values (so a CI-injected env var wins over `.env`, but a test patch made *after* import doesn't get a second `load_dotenv` call to materialize). This makes per-test config customization brittle and non-obvious.

**Fix:** move `load_dotenv()` into `Config.__init__` (called per construction) or into `main()` (called once at CLI entry). Tests then control whether `.env` loading happens by constructing `Config()` themselves.

---

### 20. `Storage.load_json` / `save_json` use platform default text encoding

**Where:** [src/storage.py:10-11, 17-19](src/storage.py:10)

```python
with open(file_path, "r") as f:
    return json.load(f)
...
with tempfile.NamedTemporaryFile(mode="w", dir=file_path.parent, delete=False, suffix=".tmp") as f:
    json.dump(data, f, indent=2)
```

Neither call specifies `encoding="utf-8"`. On hosts where the default is anything else (Windows often defaults to `cp1252`, some Linux distros to `ascii` if `LANG`/`LC_ALL` is unset, which is the case in minimal Docker images and some cron environments), unicode in any normalized field — accented politician names, em-dashes in issuer descriptions — can raise `UnicodeEncodeError` on save or `UnicodeDecodeError` on load, killing the run.

GitHub Actions Ubuntu runners default to UTF-8, so this isn't biting in CI today. It would on a self-hosted runner or any non-default deployment.

**Fix:** pass `encoding="utf-8"` to both `open` and `NamedTemporaryFile`. Standard hardening for any production JSON I/O.
