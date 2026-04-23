# Requirements

## Python Dependencies

The Congressional Trade Watcher requires the following Python packages:

### Core Dependencies

- **httpx** - Modern HTTP client library for Python
  - Used for making API requests to Financial Modeling Prep
  - Supports async operations and retries
  - Version: Latest stable

- **python-dotenv** - Loads environment variables from .env files
  - Used for configuration management
  - Allows storing API keys outside of source code
  - Version: Latest stable

## Installation

Install dependencies using pip:

```bash
pip install -r requirements.txt
```

Or with verbose output:

```bash
pip install -r requirements.txt -v
```

## Python Version

- **Required**: Python 3.11 or higher
- **Tested**: Python 3.11+

## Standard Library Usage

The application also uses the following from the Python standard library:

- `json` - JSON parsing and serialization
- `hashlib` - SHA-256 hashing for deduplication
- `logging` - Structured logging
- `pathlib` - Path handling
- `datetime` - Date and time operations
- `argparse` - Command-line argument parsing
- `tempfile` - Atomic file operations

## Optional Dependencies

The following are NOT required for v1.0:

- Database libraries (planned for v2.0)
- Email libraries (planned for v2.0)
- Web framework (planned for v2.0)

## Updating Dependencies

To update to the latest versions:

```bash
pip install --upgrade -r requirements.txt
```