from __future__ import annotations

from pathlib import Path

from .io import write_text_atomic
from .models import ProjectIndex, ProjectInfo
from .parser import analyze_file
from .renderers import render_json, render_tree
from .scanner import (
    DEFAULT_EXCLUDE_DIRS,
    DEFAULT_EXCLUDE_EXTENSIONS,
    DEFAULT_EXCLUDE_FILE_PATTERNS,
    collect_project_files,
    load_gitignore,
)


def generate_index(
    src_root: str,
    *,
    output: str | None = None,
    output_format: str = "all",
    custom_excludes: list[str] | None = None,
    include_hidden: bool = False,
    no_default_excludes: bool = False,
    no_gitignore: bool = False,
) -> ProjectIndex:
    """Generate the structured index and requested output files."""
    src_root_path = Path(src_root).expanduser().resolve()

    if not src_root_path.exists():
        raise ValueError(f"Target path does not exist: {src_root_path}")

    if not src_root_path.is_dir():
        raise ValueError(f"Target path is not a directory: {src_root_path}")

    if output is None:
        output_dir = src_root_path / "codebase-index"
    else:
        output_path = Path(output).expanduser()
        if output_path.is_absolute():
            output_dir = output_path.resolve()
        else:
            output_dir = (Path.cwd() / output_path).resolve()

    json_path = output_dir / "index.json"
    tree_path = output_dir / "tree.txt"
    output_files = {
        json_path.resolve(),
        tree_path.resolve(),
    }

    if no_default_excludes:
        exclude_dirs: set[str] = set()
        exclude_file_patterns: set[str] = set()
        exclude_extensions: set[str] = set()
    else:
        exclude_dirs = set(DEFAULT_EXCLUDE_DIRS)
        exclude_file_patterns = set(DEFAULT_EXCLUDE_FILE_PATTERNS)
        exclude_extensions = set(DEFAULT_EXCLUDE_EXTENSIONS)

    custom_excludes = custom_excludes or []
    gitignore = None if no_gitignore else load_gitignore(src_root_path)

    all_files = collect_project_files(
        src_root_path,
        exclude_dirs=exclude_dirs,
        exclude_file_patterns=exclude_file_patterns,
        exclude_extensions=exclude_extensions,
        custom_excludes=custom_excludes,
        include_hidden=include_hidden,
        output_dir=output_dir,
        output_files=output_files,
        gitignore=gitignore,
    )

    project_index = ProjectIndex(
        project=ProjectInfo(name=src_root_path.name),
    )

    for filepath in all_files:
        if filepath.suffix.lower() != ".py":
            continue

        module, error = analyze_file(filepath, src_root_path)

        if module is not None:
            project_index.modules.append(module)

        if error is not None:
            project_index.errors.append(error)

    project_index.modules.sort(key=lambda module: module.path.lower())
    project_index.errors.sort(key=lambda error: error.path.lower())

    output_dir.mkdir(parents=True, exist_ok=True)

    if output_format in {"all", "json"}:
        write_text_atomic(
            json_path,
            render_json(project_index),
        )

    if output_format in {"all", "tree"}:
        write_text_atomic(
            tree_path,
            render_tree(project_index, all_files, src_root_path),
        )

    total_classes = sum(
        len(module.classes)
        for module in project_index.modules
    )
    total_methods = sum(
        len(cls.methods)
        for module in project_index.modules
        for cls in module.classes
    )
    total_functions = sum(
        len(module.functions)
        for module in project_index.modules
    )

    print(f"Scanning: {src_root_path}")
    print()
    print(f"Scanned {len(project_index.modules)} Python files")
    print(
        f"Indexed {total_classes} classes, "
        f"{total_methods} methods, "
        f"{total_functions} functions"
    )

    if project_index.errors:
        print(
            f"{len(project_index.errors)} Python file(s) "
            "could not be indexed"
        )

    print()
    print("Output:")

    if output_format in {"all", "json"}:
        print(f"  {json_path}")

    if output_format in {"all", "tree"}:
        print(f"  {tree_path}")

    return project_index
