from __future__ import annotations

import sys
from pathlib import Path

import pytest

from codebase_indexer import __version__
from codebase_indexer.cli import main


def test_version(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(sys, "argv", ["codebase-index", "--version"])

    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code == 0
    assert capsys.readouterr().out.strip() == f"codebase-index {__version__}"


def test_help(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(sys, "argv", ["codebase-index", "--help"])

    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code == 0
    output = capsys.readouterr().out
    assert "Generate a structured JSON index" in output
    assert "--no-gitignore" in output


def test_cli_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("def run(): pass\n", encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        ["codebase-index", str(tmp_path), "--format", "json"],
    )

    assert main() == 0
    assert (tmp_path / "codebase-index" / "index.json").exists()


def test_cli_bad_path_exits_one(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        ["codebase-index", str(tmp_path / "missing")],
    )

    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code == 1
    assert "does not exist" in capsys.readouterr().err
