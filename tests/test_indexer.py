from __future__ import annotations

import json
from pathlib import Path

import pytest

from codebase_indexer.indexer import generate_index


def test_generate_index_writes_both_outputs(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text(
        '"""Application."""\n\ndef run() -> None:\n    pass\n',
        encoding="utf-8",
    )

    index = generate_index(str(tmp_path))

    output = tmp_path / "codebase-index"
    json_path = output / "index.json"
    tree_path = output / "tree.txt"

    assert json_path.is_file()
    assert tree_path.is_file()
    assert [module.path for module in index.modules] == ["app.py"]

    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["schema_version"] == "1.0"
    assert data["project"] == {"name": tmp_path.name, "root": "."}


def test_generate_index_json_only(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("pass\n", encoding="utf-8")

    generate_index(str(tmp_path), output_format="json")

    output = tmp_path / "codebase-index"
    assert (output / "index.json").exists()
    assert not (output / "tree.txt").exists()


def test_generate_index_tree_only(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("pass\n", encoding="utf-8")

    generate_index(str(tmp_path), output_format="tree")

    output = tmp_path / "codebase-index"
    assert not (output / "index.json").exists()
    assert (output / "tree.txt").exists()


def test_duplicate_filenames_keep_project_relative_paths(tmp_path: Path) -> None:
    for folder in ("foo", "bar"):
        path = tmp_path / folder / "config.py"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("def load(): pass\n", encoding="utf-8")

    index = generate_index(str(tmp_path), output_format="json")

    assert [module.path for module in index.modules] == [
        "bar/config.py",
        "foo/config.py",
    ]


def test_syntax_error_is_nonfatal_when_other_output_is_useful(tmp_path: Path) -> None:
    (tmp_path / "good.py").write_text("def ok(): pass\n", encoding="utf-8")
    (tmp_path / "broken.py").write_text("def bad(:\n", encoding="utf-8")

    index = generate_index(str(tmp_path))

    assert [module.path for module in index.modules] == ["good.py"]
    assert len(index.errors) == 1
    assert index.errors[0].path == "broken.py"
    assert (tmp_path / "codebase-index" / "index.json").exists()


def test_missing_target_is_fatal(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="does not exist"):
        generate_index(str(tmp_path / "missing"))
