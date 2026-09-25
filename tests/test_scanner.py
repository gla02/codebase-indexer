from __future__ import annotations

from pathlib import Path

from codebase_indexer.scanner import (
    DEFAULT_EXCLUDE_DIRS,
    DEFAULT_EXCLUDE_EXTENSIONS,
    DEFAULT_EXCLUDE_FILE_PATTERNS,
    collect_project_files,
    load_gitignore,
)


def collect(
    root: Path,
    *,
    custom_excludes: list[str] | None = None,
    include_hidden: bool = False,
    no_defaults: bool = False,
    use_gitignore: bool = True,
) -> list[str]:
    output_dir = root / "codebase-index"
    files = collect_project_files(
        root,
        exclude_dirs=set() if no_defaults else set(DEFAULT_EXCLUDE_DIRS),
        exclude_file_patterns=(
            set() if no_defaults else set(DEFAULT_EXCLUDE_FILE_PATTERNS)
        ),
        exclude_extensions=(
            set() if no_defaults else set(DEFAULT_EXCLUDE_EXTENSIONS)
        ),
        custom_excludes=custom_excludes or [],
        include_hidden=include_hidden,
        output_dir=output_dir,
        output_files={
            (output_dir / "index.json").resolve(),
            (output_dir / "tree.txt").resolve(),
        },
        gitignore=load_gitignore(root) if use_gitignore else None,
    )
    return [path.relative_to(root).as_posix() for path in files]


def touch(root: Path, rel: str, content: str = "") -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_default_excludes_and_visible_project_files(tmp_path: Path) -> None:
    touch(tmp_path, "src/app.py", "def main(): pass\n")
    touch(tmp_path, "__pycache__/app.pyc")
    touch(tmp_path, ".venv/lib/tool.py", "pass\n")
    touch(tmp_path, "build/generated.py", "pass\n")
    touch(tmp_path, "README.md", "# Project\n")

    assert collect(tmp_path) == ["README.md", "src/app.py"]


def test_hidden_paths_are_excluded_but_whitelisted_metadata_is_visible(tmp_path: Path) -> None:
    touch(tmp_path, ".secret/tool.py", "pass\n")
    touch(tmp_path, ".github/workflows/test.yml", "name: test\n")
    touch(tmp_path, ".gitignore", "")

    assert collect(tmp_path) == [
        ".github/workflows/test.yml",
        ".gitignore",
    ]


def test_include_hidden_does_not_disable_default_junk_excludes(tmp_path: Path) -> None:
    touch(tmp_path, ".secret/tool.py", "pass\n")
    touch(tmp_path, ".git/config", "x\n")

    paths = collect(tmp_path, include_hidden=True)

    assert ".secret/tool.py" in paths
    assert ".git/config" not in paths


def test_custom_exclude_matches_components_and_globs(tmp_path: Path) -> None:
    touch(tmp_path, "src/app.py", "pass\n")
    touch(tmp_path, "experiments/one.py", "pass\n")
    touch(tmp_path, "tuning_results/run.json", "{}\n")
    touch(tmp_path, "tuning_results_smoke/run.json", "{}\n")

    paths = collect(
        tmp_path,
        custom_excludes=["experiments", "tuning_results*"],
    )

    assert paths == ["src/app.py"]


def test_output_directory_is_always_excluded(tmp_path: Path) -> None:
    touch(tmp_path, "src/app.py", "pass\n")
    touch(tmp_path, "codebase-index/index.json", "{}\n")
    touch(tmp_path, "codebase-index/tree.txt", "tree\n")
    touch(tmp_path, "codebase-index/other.py", "pass\n")

    assert collect(tmp_path) == ["src/app.py"]


def test_gitignore_ignores_matching_files(tmp_path: Path) -> None:
    touch(tmp_path, ".gitignore", "runs/\n*.log\n")
    touch(tmp_path, "src/app.py", "pass\n")
    touch(tmp_path, "runs/result.json", "{}\n")
    touch(tmp_path, "debug.log", "noise\n")

    paths = collect(tmp_path)

    assert paths == [".gitignore", "src/app.py"]


def test_gitignore_negation_reincludes_child_when_parent_is_traversable(tmp_path: Path) -> None:
    # This is the important Git-style negation case: the directory itself is
    # not ignored; its contents are, then one file is re-included.
    touch(tmp_path, ".gitignore", "generated/*\n!generated/keep.py\n")
    touch(tmp_path, "generated/drop.py", "pass\n")
    touch(tmp_path, "generated/keep.py", "pass\n")

    paths = collect(tmp_path)

    assert paths == [".gitignore", "generated/keep.py"]


def test_gitignore_cannot_reinclude_file_from_ignored_parent_directory(tmp_path: Path) -> None:
    # Matches Git semantics: once the parent directory itself is excluded,
    # a child cannot be re-included by a later negation pattern.
    touch(tmp_path, ".gitignore", "generated/\n!generated/keep.py\n")
    touch(tmp_path, "generated/drop.py", "pass\n")
    touch(tmp_path, "generated/keep.py", "pass\n")

    paths = collect(tmp_path)

    assert paths == [".gitignore"]


def test_no_gitignore_leaves_gitignored_files_visible(tmp_path: Path) -> None:
    touch(tmp_path, ".gitignore", "generated/\n")
    touch(tmp_path, "generated/keep.py", "pass\n")

    paths = collect(tmp_path, use_gitignore=False)

    assert paths == [".gitignore", "generated/keep.py"]


def test_no_default_excludes_is_independent_from_hidden_filtering(tmp_path: Path) -> None:
    touch(tmp_path, "build/generated.py", "pass\n")
    touch(tmp_path, ".secret/private.py", "pass\n")

    paths = collect(tmp_path, no_defaults=True)

    assert "build/generated.py" in paths
    assert ".secret/private.py" not in paths
