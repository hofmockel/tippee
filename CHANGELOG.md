# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial implementation of Congressional Trade Watcher
- Support for monitoring Senate and House trade disclosures
- Discord webhook alerts for new disclosures
- Deduplication using SHA-256 fingerprints
- CLI with run, test-alert, and backfill commands
- Comprehensive documentation and user manual
- Unit tests for core functionality
- Cron scheduling support

### Changed
- Updated watchlist to include 15 symbols: ARM, GEV, NVDA, TSM, TPL, STX, ANET, VRT, ETN, EQIX, NVT, AVGO, APD, LITE, ASML

### Technical Details
- Python 3.11+ with minimal dependencies (httpx only)
- Local JSON storage for persistence
- Financial Modeling Prep API integration
- Exponential backoff for retries
- Structured logging

## [1.0.0] - 2026-04-23

### Added
- Complete system implementation
- Documentation suite
- Test coverage
- Open source licensing (MIT)