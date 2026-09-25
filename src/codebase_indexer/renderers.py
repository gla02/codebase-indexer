from __future__ import annotations

import json
from pathlib import Path

from .models import ProjectIndex


def describe_non_indexed_file(name: str) -> str:
    """Return a compact description for common non-Python project files."""
    path = Path(name)
    suffix = path.suffix.lower()
    lower_name = name.lower()

    if lower_name == "dockerfile":
        return "Dockerfile"

    if lower_name in {"makefile", "justfile"}:
        return "task runner file"

    if lower_name in {"requirements.txt", "constraints.txt"}:
        return "Python dependencies"

    if lower_name == "pyproject.toml":
        return "Python project config"

    if lower_name == "setup.py":
        return "Python package setup"

    if lower_name == "setup.cfg":
        return "Python/package config"

    if lower_name == "poetry.lock":
        return "Poetry lockfile"

    if lower_name == "pdm.lock":
        return "PDM lockfile"

    if lower_name == "uv.lock":
        return "uv lockfile"

    if lower_name == "package.json":
        return "Node/package config"

    if lower_name in {
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
    }:
        return "Node lockfile"

    if lower_name in {
        ".env.example",
        ".env.template",
        ".env.sample",
    }:
        return "environment config template"

    if lower_name in {
        "readme.md",
        "readme.rst",
        "readme.txt",
    }:
        return "project README"

    if lower_name in {
        "license",
        "license.md",
        "license.txt",
    }:
        return "license"

    if lower_name in {".gitignore", ".dockerignore"}:
        return "ignore rules"

    if lower_name in {
        ".pre-commit-config.yaml",
        ".pre-commit-config.yml",
    }:
        return "pre-commit config"

    descriptions = {
        ".html": "HTML template/page",
        ".htm": "HTML template/page",
        ".css": "stylesheet",
        ".scss": "stylesheet",
        ".sass": "stylesheet",
        ".less": "stylesheet",
        ".js": "JavaScript",
        ".mjs": "JavaScript module",
        ".cjs": "CommonJS JavaScript",
        ".ts": "TypeScript",
        ".tsx": "React/TSX component",
        ".jsx": "React/JSX component",
        ".json": "JSON config/data",
        ".jsonl": "JSONL data",
        ".yaml": "YAML config",
        ".yml": "YAML config",
        ".toml": "TOML config",
        ".ini": "INI config",
        ".cfg": "config",
        ".conf": "config",
        ".md": "Markdown docs",
        ".rst": "reStructuredText docs",
        ".txt": "text file",
        ".csv": "CSV data",
        ".tsv": "TSV data",
        ".sql": "SQL script",
        ".sh": "shell script",
        ".bash": "shell script",
        ".zsh": "shell script",
        ".bat": "batch script",
        ".ps1": "PowerShell script",
        ".ipynb": "Jupyter notebook",
    }

    return descriptions.get(suffix, "")


def build_tree_structure(
    project_index: ProjectIndex,
    all_files: list[Path],
    src_root: Path,
) -> str:
    """Build the compact human-readable project tree."""
    modules_by_path = {
        module.path: module
        for module in project_index.modules
    }
    errors_by_path = {
        error.path: error
        for error in project_index.errors
    }

    lines = [
        project_index.project.name,
        f"{len(all_files)} files shown",
        f"{len(project_index.modules)} Python files indexed",
    ]

    if project_index.errors:
        lines.append(
            f"{len(project_index.errors)} Python files with errors"
        )

    lines.append("")

    dir_structure: dict[str, dict] = {}

    for filepath in all_files:
        rel_path = filepath.relative_to(src_root)
        rel_str = rel_path.as_posix()
        current = dir_structure

        for part in rel_path.parts[:-1]:
            current = current.setdefault(
                part,
                {"__children__": {}},
            )["__children__"]

        current[rel_path.parts[-1]] = {
            "__file__": True,
            "__path__": rel_str,
        }

    def format_file_line(
        name: str,
        value: dict,
        prefix: str,
        connector: str,
    ) -> str:
        rel_path = value["__path__"]
        module = modules_by_path.get(rel_path)
        error = errors_by_path.get(rel_path)

        line = f"{prefix}{connector}{name}"

        if error is not None:
            return line + f" [index error: {error.error_type}]"

        if module is None:
            description = describe_non_indexed_file(name)

            if description:
                line += f" # {description}"

            return line

        class_count = len(module.classes)
        method_count = sum(
            len(cls.methods)
            for cls in module.classes
        )
        func_count = len(module.functions)

        counts: list[str] = []

        if class_count:
            counts.append(f"{class_count}c")

        if method_count:
            counts.append(f"{method_count}m")

        if func_count:
            counts.append(f"{func_count}f")

        if counts:
            line += f" [{' / '.join(counts)}]"

        primary_name = ""
        primary_type = ""
        primary_summary = ""

        if module.classes:
            primary = module.classes[0]
            primary_name = primary.name
            primary_type = "class"
            primary_summary = primary.summary or ""
        elif module.functions:
            primary = module.functions[0]
            primary_name = primary.name
            primary_type = "function"
            primary_summary = primary.summary or ""
        elif module.summary:
            primary_name = "module"
            primary_type = "module"
            primary_summary = module.summary

        if primary_summary:
            if len(primary_summary) > 58:
                primary_summary = primary_summary[:55] + "..."

            line += f" # {primary_name}: {primary_summary}"
        elif primary_name:
            line += f" # {primary_name} ({primary_type})"

        return line

    def render_tree(
        structure: dict,
        prefix: str = "",
    ) -> list[str]:
        result: list[str] = []
        dirs = []
        files = []

        for name, value in structure.items():
            if "__file__" in value:
                files.append((name, value))
            else:
                dirs.append((name, value))

        dirs.sort(key=lambda item: item[0].lower())
        files.sort(key=lambda item: item[0].lower())
        items = dirs + files

        for index, (name, value) in enumerate(items):
            is_last = index == len(items) - 1
            connector = "└── " if is_last else "├── "
            child_prefix = (
                prefix + ("    " if is_last else "│   ")
            )

            if "__file__" in value:
                result.append(
                    format_file_line(
                        name,
                        value,
                        prefix,
                        connector,
                    )
                )
            else:
                result.append(
                    f"{prefix}{connector}{name}/"
                )
                result.extend(
                    render_tree(
                        value["__children__"],
                        child_prefix,
                    )
                )

        return result

    lines.extend(render_tree(dir_structure))

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

    lines.append("")
    lines.append(
        "Total indexed Python: "
        f"{len(project_index.modules)} files, "
        f"{total_classes} classes, "
        f"{total_methods} methods, "
        f"{total_functions} functions"
    )

    if project_index.errors:
        lines.append(
            f"Index errors: {len(project_index.errors)}"
        )

    return "\n".join(lines)


def render_json(project_index: ProjectIndex) -> str:
    """Render the canonical JSON representation."""
    return json.dumps(
        project_index.to_dict(),
        indent=2,
        ensure_ascii=False,
    ) + "\n"


def render_tree(
    project_index: ProjectIndex,
    all_files: list[Path],
    src_root: Path,
) -> str:
    """Render the human-readable project tree."""
    return (
        build_tree_structure(
            project_index,
            all_files,
            src_root,
        )
        + "\n"
    )
