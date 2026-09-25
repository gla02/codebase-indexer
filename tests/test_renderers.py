from __future__ import annotations

from pathlib import Path

from codebase_indexer.models import (
    ClassInfo,
    FunctionInfo,
    ModuleInfo,
    ProjectIndex,
    ProjectInfo,
)
from codebase_indexer.renderers import render_json, render_tree


def test_json_schema_has_stable_top_level_shape() -> None:
    index = ProjectIndex(project=ProjectInfo(name="demo"))

    rendered = render_json(index)

    assert rendered.startswith('{\n  "schema_version": "1.0",')
    assert '"project": {' in rendered
    assert '"modules": []' in rendered
    assert '"errors": []' in rendered


def test_tree_is_deterministic_and_directories_precede_files(tmp_path: Path) -> None:
    files = [
        tmp_path / "z.py",
        tmp_path / "pkg" / "b.py",
        tmp_path / "pkg" / "a.py",
        tmp_path / "README.md",
    ]
    for path in files:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")

    index = ProjectIndex(
        project=ProjectInfo(name="demo"),
        modules=[
            ModuleInfo(
                path="pkg/a.py",
                line_count=10,
                summary="Package helper.",
                classes=[
                    ClassInfo(
                        name="Runner",
                        line=1,
                        end_line=8,
                        methods=[
                            FunctionInfo(
                                name="run",
                                signature="run(self)",
                                line=2,
                                end_line=3,
                                kind="method",
                            )
                        ],
                    )
                ],
            ),
            ModuleInfo(
                path="pkg/b.py",
                line_count=2,
                functions=[
                    FunctionInfo(
                        name="helper",
                        signature="helper()",
                        line=1,
                        end_line=1,
                    )
                ],
            ),
            ModuleInfo(path="z.py", line_count=1),
        ],
    )

    tree = render_tree(index, files, tmp_path)

    assert tree.index("├── pkg/") < tree.index("├── README.md")
    assert tree.index("a.py") < tree.index("b.py")
    assert "a.py [1c / 1m] # Runner (class)" in tree
    assert "b.py [1f] # helper (function)" in tree
    assert "README.md # project README" in tree
    assert "Total indexed Python: 3 files, 1 classes, 1 methods, 1 functions" in tree
