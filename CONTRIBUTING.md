# Contributing to Congressional Trade Watcher

Thank you for your interest in contributing to the Congressional Trade Watcher project! We welcome contributions from the community.

## How to Contribute

### Reporting Issues
- Use GitHub Issues to report bugs or request features
- Provide detailed steps to reproduce bugs
- Include relevant log output and system information

### Code Contributions
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass: `python -m pytest tests/`
6. Commit your changes: `git commit -m "Add your feature"`
7. Push to your fork: `git push origin feature/your-feature`
8. Create a Pull Request

### Development Setup
- Follow the installation instructions in [INSTALL.md](INSTALL.md)
- Use Python 3.11+
- Install dependencies: `pip install -r requirements.txt`
- Copy `.env.example` to `.env` and add test values
- Run tests before submitting: `python -m pytest tests/`

### Project Structure
Understanding the codebase:
- `src/main.py` - Entry point and CLI commands
- `src/config.py` - Configuration and environment loading
- `src/client.py` - FMP API client
- `src/normalize.py` - Record normalization logic
- `src/dedupe.py` - Deduplication using fingerprints
- `src/alerts.py` - Discord and console alerting
- `src/storage.py` - JSON file persistence
- `src/models.py` - Type definitions
- `tests/` - Unit tests for core functionality
- `config/watchlist.json` - User's watched symbols
- `data/` - Runtime data (seen hashes, last run info)
- `logs/` - Application logs
- `docs/` - Detailed documentation

### Code Style
- Follow PEP 8 style guidelines
- Use type hints where appropriate
- Write clear, concise commit messages
- Add docstrings to functions and classes

### Testing
- Add unit tests for new features
- Ensure existing tests still pass
- Test edge cases and error conditions

## Code of Conduct
Please review our CODE_OF_CONDUCT.md before contributing.

## Questions
If you have questions, feel free to open an issue or contact the maintainers.