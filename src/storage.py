import json
import tempfile
from pathlib import Path
from typing import Dict, Any, Set

class Storage:
    @staticmethod
    def load_json(file_path: Path) -> Dict[str, Any]:
        if not file_path.exists():
            return {}
        with open(file_path, "r") as f:
            return json.load(f)

    @staticmethod
    def save_json(file_path: Path, data: Dict[str, Any]) -> None:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", dir=file_path.parent, delete=False, suffix=".tmp") as f:
                temp_path = Path(f.name)
                json.dump(data, f, indent=2)
            temp_path.replace(file_path)
            temp_path = None  # rename succeeded; nothing to clean up
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)

    @staticmethod
    def load_seen_hashes() -> Set[str]:
        data = Storage.load_json(Path("data/seen_hashes.json"))
        return set(data.get("hashes", []))

    @staticmethod
    def save_seen_hashes(hashes: Set[str]) -> None:
        data = {"hashes": list(hashes)}
        Storage.save_json(Path("data/seen_hashes.json"), data)

    @staticmethod
    def load_last_run() -> Dict[str, Any]:
        return Storage.load_json(Path("data/last_run.json"))

    @staticmethod
    def save_last_run(data: Dict[str, Any]) -> None:
        Storage.save_json(Path("data/last_run.json"), data)