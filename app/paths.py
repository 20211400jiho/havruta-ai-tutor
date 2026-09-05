"""Stable paths shared by local commands and the backend Docker image."""

from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]


def resolve_chroma_dir(value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else PROJECT_DIR / path
