from pathlib import Path

# Project root: this file is src/utils/path.py, so parents[2] is the repo root.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def return_full_path(relative_path: str) -> str:
    """Resolve ``relative_path`` against the project root and return it as an
    absolute path string, so files like ``.env`` load regardless of the current
    working directory."""
    return str(_PROJECT_ROOT / relative_path)
