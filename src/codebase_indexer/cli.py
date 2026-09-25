from __future__ import annotations

import argparse

from . import __version__
from .indexer import generate_index


def build_arg_parser() -> argparse.ArgumentParser:
    """Create the command-line parser."""
    parser = argparse.ArgumentParser(
        prog="codebase-index",
        description=(
            "Generate a structured JSON index and compact project tree "
            "for a Python codebase."
        ),
    )

    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="project directory to scan (default: current directory)",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="output directory (default: <project>/codebase-index)",
    )
    parser.add_argument(
        "--format",
        choices=("all", "json", "tree"),
        default="all",
        help="output format to generate (default: all)",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="PATTERN",
        help="additional exclusion glob; may be repeated",
    )
    parser.add_argument(
        "--include-hidden",
        action="store_true",
        help="include hidden files/directories except default exclusions",
    )
    parser.add_argument(
        "--no-default-excludes",
        action="store_true",
        help="disable built-in directory, file, and extension exclusions",
    )
    parser.add_argument(
        "--no-gitignore",
        action="store_true",
        help="do not apply rules from the project-root .gitignore",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    return parser


def main() -> int:
    """CLI entry point."""
    parser = build_arg_parser()
    args = parser.parse_args()

    try:
        generate_index(
            src_root=args.path,
            output=args.output,
            output_format=args.format,
            custom_excludes=args.exclude,
            include_hidden=args.include_hidden,
            no_default_excludes=args.no_default_excludes,
            no_gitignore=args.no_gitignore,
        )
    except (OSError, ValueError) as exc:
        parser.exit(1, f"error: {exc}\n")

    return 0
