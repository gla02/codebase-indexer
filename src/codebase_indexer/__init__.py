"""Codebase Indexer package."""

from .indexer import generate_index
from .models import (
    SCHEMA_VERSION,
    ClassInfo,
    FunctionInfo,
    IndexError,
    ModuleInfo,
    ProjectIndex,
    ProjectInfo,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "SCHEMA_VERSION",
    "ClassInfo",
    "FunctionInfo",
    "IndexError",
    "ModuleInfo",
    "ProjectIndex",
    "ProjectInfo",
    "generate_index",
]
