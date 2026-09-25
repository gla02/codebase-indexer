from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


SCHEMA_VERSION = "1.0"


@dataclass(slots=True)
class FunctionInfo:
    """Structural information about a Python function or method."""

    name: str
    signature: str
    line: int
    end_line: int
    summary: str | None = None
    is_async: bool = False
    kind: str = "function"


@dataclass(slots=True)
class ClassInfo:
    """Structural information about a Python class."""

    name: str
    line: int
    end_line: int
    bases: list[str] = field(default_factory=list)
    summary: str | None = None
    methods: list[FunctionInfo] = field(default_factory=list)


@dataclass(slots=True)
class ModuleInfo:
    """Structural information extracted from one Python source file."""

    path: str
    line_count: int
    summary: str | None = None
    classes: list[ClassInfo] = field(default_factory=list)
    functions: list[FunctionInfo] = field(default_factory=list)


@dataclass(slots=True)
class IndexError:
    """A non-fatal error encountered while indexing a project."""

    path: str
    error_type: str
    message: str
    line: int | None = None


@dataclass(slots=True)
class ProjectInfo:
    """Basic metadata about the indexed project."""

    name: str
    root: str = "."


@dataclass(slots=True)
class ProjectIndex:
    """Complete structural index for a Python project."""

    project: ProjectInfo
    modules: list[ModuleInfo] = field(default_factory=list)
    errors: list[IndexError] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return the canonical JSON representation of the index."""
        return {
            "schema_version": SCHEMA_VERSION,
            "project": asdict(self.project),
            "modules": [asdict(module) for module in self.modules],
            "errors": [asdict(error) for error in self.errors],
        }
