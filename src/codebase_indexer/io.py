from __future__ import annotations

from pathlib import Path


def write_text_atomic(path: Path, content: str) -> None:
    """Write a text file via a temporary sibling and replace the destination."""
    path.parent.mkdir(parents=True, exist_ok=True)

    temp_path = path.with_name(path.name + ".tmp")
    temp_path.write_text(content, encoding="utf-8")
    temp_path.replace(path)
