from __future__ import annotations

import fnmatch
import os
from pathlib import Path

import pathspec


DEFAULT_EXCLUDE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".nox",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "dist",
    "build",
    ".next",
}

DEFAULT_EXCLUDE_FILE_PATTERNS = {
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.so",
    "*.dll",
    "*.dylib",
    ".DS_Store",
    "*.egg-info",
    "*.log",
}

DEFAULT_EXCLUDE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".svg",
    ".mp4",
    ".mov",
    ".avi",
    ".mp3",
    ".wav",
    ".zip",
    ".tar",
    ".gz",
    ".7z",
    ".rar",
    ".parquet",
    ".feather",
    ".arrow",
    ".pkl",
    ".pickle",
    ".joblib",
    ".pt",
    ".pth",
    ".onnx",
    ".h5",
    ".hdf5",
    ".sqlite",
    ".db",
}

DEFAULT_VISIBLE_HIDDEN_FILES = {
    ".gitignore",
    ".dockerignore",
    ".pre-commit-config.yaml",
    ".pre-commit-config.yml",
    ".env.example",
    ".env.template",
    ".env.sample",
}

DEFAULT_VISIBLE_HIDDEN_DIRS = {
    ".github",
}


def is_hidden_path(rel_path: Path) -> bool:
    """Return True when a relative path contains hidden components."""
    for index, part in enumerate(rel_path.parts):
        if not part.startswith(".") or part in {".", ".."}:
            continue

        if part in DEFAULT_VISIBLE_HIDDEN_DIRS:
            continue

        if (
            index == len(rel_path.parts) - 1
            and part in DEFAULT_VISIBLE_HIDDEN_FILES
        ):
            continue

        return True

    return False


def matches_custom_exclude(
    rel_path: Path,
    patterns: list[str],
) -> bool:
    """Match user exclusions against names, components, and relative paths."""
    rel_posix = rel_path.as_posix()

    for pattern in patterns:
        normalized = pattern.replace("\\", "/")

        if fnmatch.fnmatch(rel_posix, normalized):
            return True

        if any(fnmatch.fnmatch(part, pattern) for part in rel_path.parts):
            return True

    return False


def load_gitignore(src_root: Path) -> pathspec.PathSpec | None:
    """Load the project-root .gitignore if one exists."""
    gitignore_path = src_root / ".gitignore"

    if not gitignore_path.is_file():
        return None

    try:
        lines = gitignore_path.read_text(
            encoding="utf-8",
        ).splitlines()
    except UnicodeDecodeError:
        lines = gitignore_path.read_text(
            encoding="utf-8-sig",
        ).splitlines()

    return pathspec.GitIgnoreSpec.from_lines(lines)


def is_gitignored(
    rel_path: Path,
    *,
    is_dir: bool,
    gitignore: pathspec.PathSpec | None,
) -> bool:
    """Return True if a project-relative path matches the root .gitignore."""
    if gitignore is None:
        return False

    path = rel_path.as_posix()

    if is_dir:
        path += "/"

    return gitignore.match_file(path)


def should_exclude_path(
    path: Path,
    src_root: Path,
    *,
    exclude_dirs: set[str],
    exclude_file_patterns: set[str],
    exclude_extensions: set[str],
    custom_excludes: list[str],
    include_hidden: bool,
    output_dir: Path,
    output_files: set[Path],
    gitignore: pathspec.PathSpec | None,
) -> bool:
    """Return True if a file or directory should be excluded."""
    try:
        rel = path.relative_to(src_root)
    except ValueError:
        return True

    resolved = path.resolve()

    if resolved in output_files:
        return True

    if output_dir != src_root:
        try:
            resolved.relative_to(output_dir)
            return True
        except ValueError:
            pass

    if not include_hidden and is_hidden_path(rel):
        return True

    if matches_custom_exclude(rel, custom_excludes):
        return True

    if is_gitignored(
        rel,
        is_dir=path.is_dir(),
        gitignore=gitignore,
    ):
        return True

    dir_parts = rel.parts if path.is_dir() else rel.parts[:-1]

    for part in dir_parts:
        if part in exclude_dirs or part.endswith(".egg-info"):
            return True

    if path.is_file():
        if path.suffix.lower() in exclude_extensions:
            return True

        if any(
            fnmatch.fnmatch(path.name, pattern)
            for pattern in exclude_file_patterns
        ):
            return True

    return False


def collect_project_files(
    src_root: Path,
    *,
    exclude_dirs: set[str],
    exclude_file_patterns: set[str],
    exclude_extensions: set[str],
    custom_excludes: list[str],
    include_hidden: bool,
    output_dir: Path,
    output_files: set[Path],
    gitignore: pathspec.PathSpec | None,
) -> list[Path]:
    """Collect relevant project files while pruning excluded directories."""
    files: list[Path] = []

    for current_root, dirnames, filenames in os.walk(src_root):
        current = Path(current_root)
        kept_dirs: list[str] = []

        for dirname in sorted(dirnames, key=str.lower):
            candidate = current / dirname

            if not should_exclude_path(
                candidate,
                src_root,
                exclude_dirs=exclude_dirs,
                exclude_file_patterns=exclude_file_patterns,
                exclude_extensions=exclude_extensions,
                custom_excludes=custom_excludes,
                include_hidden=include_hidden,
                output_dir=output_dir,
                output_files=output_files,
                gitignore=gitignore,
            ):
                kept_dirs.append(dirname)

        dirnames[:] = kept_dirs

        for filename in sorted(filenames, key=str.lower):
            candidate = current / filename

            if should_exclude_path(
                candidate,
                src_root,
                exclude_dirs=exclude_dirs,
                exclude_file_patterns=exclude_file_patterns,
                exclude_extensions=exclude_extensions,
                custom_excludes=custom_excludes,
                include_hidden=include_hidden,
                output_dir=output_dir,
                output_files=output_files,
                gitignore=gitignore,
            ):
                continue

            files.append(candidate)

    return sorted(
        files,
        key=lambda path: path.relative_to(src_root).as_posix().lower(),
    )
