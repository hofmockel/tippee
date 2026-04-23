# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
