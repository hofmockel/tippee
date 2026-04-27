# Architectural Decisions

This document records key architectural decisions for the Congressional Trade Watcher.

## Data Source
Use Financial Modeling Prep's stable Senate and House trade endpoints as the sole upstream source. Chosen for:
- Free plan available
- Publicly documented endpoints
- Daily updates
- No scraping required

## Storage
Use simple local JSON files for persistence (seen_hashes.json, last_run.json). Chosen for:
- No database dependency
- Human-readable format
- Atomic writes with tempfile
- Easy backup/restore

## Language and Runtime
Python 3.11+ for:
- Modern async support (though not used here)
- Type hints with TypedDict
- Standard library richness

## Dependencies
Minimal dependencies:
- httpx for HTTP requests (async-capable, modern)
- python-dotenv for environment variable management
- No pydantic (kept simple with dicts and TypedDict)
- No pandas or heavy libs

## CLI Framework
argparse for command-line interface. Chosen for:
- Standard library
- Simple subcommands (run, test-alert, backfill)
- Built-in help

## Deduplication
SHA-256 fingerprinting on stable record fields. Chosen for:
- Deterministic and collision-resistant
- No reliance on upstream IDs
- Persists seen hashes locally

## Rate Limiting
Conservative 1-second delay between requests. Chosen for:
- Respect API limits
- Simple implementation
- Avoids complex rate limiting logic

## Error Handling
Fail gracefully per symbol/endpoint, continue processing. Chosen for:
- Resilience to partial failures
- Comprehensive logging
- Exponential backoff retries

## Alerting
Console logs + Discord webhooks. Chosen for:
- Simple, no email server setup
- Discord for real-time notifications
- Easy to extend (e.g., add email later)

## Scheduling
Designed for cron, not always-on. Chosen for:
- No server/process management
- Reliable with system scheduler
- Low resource usage

## Testing
Unit tests for core functions (normalize, dedupe). Chosen for:
- Validate critical logic
- Easy to run
- No integration tests (external API)

## Alert Noise Policy

Default behavior is now to send alerts only when there is a new disclosure to report.

- `SEND_CONFIRMATION_ALERT=false` by default to avoid noisy no-op notifications.
- Operators can opt-in to heartbeat messages by setting `SEND_CONFIRMATION_ALERT=true`.
- `CONFIRMATION_MESSAGE` controls the heartbeat content if enabled.
