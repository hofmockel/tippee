import json
import logging
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, Set

logger = logging.getLogger(__name__)

# Anchor data files at the project root so the CLI works no matter what CWD it
# was launched from. (Mirrors the watchlist-path fix in src/config.py.)
_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_SEEN_HASHES_PATH = _DATA_DIR / "seen_hashes.json"
_LAST_RUN_PATH = _DATA_DIR / "last_run.json"


class Storage:
    @staticmethod
    def load_json(file_path: Path) -> Dict[str, Any]:
        if not file_path.exists():
            return {}
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            # A corrupt or unreadable state file shouldn't kill the run.
            # Treat as empty so dedupe degrades to "alert spam" rather than
            # "permanent crash with no alerts."
            logger.error(
                "Failed to read %s (%s); treating as empty. Inspect the file before next run.",
                file_path, e,
            )
            return {}

    @staticmethod
    def save_json(file_path: Path, data: Dict[str, Any], *, indent: Optional[int] = 2) -> None:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=file_path.parent, delete=False, suffix=".tmp") as f:
                temp_path = Path(f.name)
                json.dump(data, f, indent=indent)
            temp_path.replace(file_path)
            temp_path = None  # rename succeeded; nothing to clean up
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)

    @staticmethod
    def load_seen_hashes() -> Set[str]:
        data = Storage.load_json(_SEEN_HASHES_PATH)
        raw = data.get("hashes", [])
        if not isinstance(raw, list):
            # Hand-edited or otherwise corrupted state. set("abc") would
            # silently produce 3 single-char fingerprints that match nothing
            # (re-flooding alerts) — refuse and treat as empty instead.
            logger.error(
                "seen_hashes.json contains 'hashes' that isn't a list (got %s); "
                "treating as empty. Inspect the file before next run.",
                type(raw).__name__,
            )
            return set()
        return {h for h in raw if isinstance(h, str)}

    @staticmethod
    def save_seen_hashes(hashes: Set[str]) -> None:
        # sorted so the file is byte-stable across runs whose hash set didn't
        # change. indent=None keeps the file compact — no human reads thousands
        # of opaque hashes, so per-line indentation just wastes space.
        data = {"hashes": sorted(hashes)}
        Storage.save_json(_SEEN_HASHES_PATH, data, indent=None)

    @staticmethod
    def load_last_run() -> Dict[str, Any]:
        return Storage.load_json(_LAST_RUN_PATH)

    @staticmethod
    def save_last_run(data: Dict[str, Any]) -> None:
        Storage.save_json(_LAST_RUN_PATH, data)
