from __future__ import annotations

import ast
import tokenize
from pathlib import Path

from .models import ClassInfo, FunctionInfo, IndexError, ModuleInfo


def get_summary(docstring: str | None) -> str | None:
    """Extract the first non-empty docstring line as a compact summary."""
    if not docstring:
        return None

    for line in docstring.strip().splitlines():
        line = line.strip()
        if line:
            return line[:117] + "..." if len(line) > 120 else line

    return None


def _unparse(node: ast.AST | None) -> str:
    """Return source-like text for an AST node."""
    if node is None:
        return ""

    return ast.unparse(node)


def _format_arg(
    arg: ast.arg,
    default: ast.AST | None = None,
) -> str:
    """Render one function argument."""
    text = arg.arg

    if arg.annotation is not None:
        text += f": {_unparse(arg.annotation)}"

    if default is not None:
        text += f" = {_unparse(default)}"

    return text


def build_signature(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> str:
    """Build a source-like function signature from AST data."""
    args = node.args
    parts: list[str] = []

    positional = [*args.posonlyargs, *args.args]
    defaults: list[ast.AST | None] = [None] * (
        len(positional) - len(args.defaults)
    )
    defaults.extend(args.defaults)

    posonly_count = len(args.posonlyargs)

    for index, (arg, default) in enumerate(zip(positional, defaults)):
        parts.append(_format_arg(arg, default))

        if posonly_count and index + 1 == posonly_count:
            parts.append("/")

    if args.vararg is not None:
        parts.append(f"*{_format_arg(args.vararg)}")
    elif args.kwonlyargs:
        parts.append("*")

    for arg, default in zip(args.kwonlyargs, args.kw_defaults):
        parts.append(_format_arg(arg, default))

    if args.kwarg is not None:
        parts.append(f"**{_format_arg(args.kwarg)}")

    type_params = getattr(node, "type_params", None)
    type_param_text = ""

    if type_params:
        type_param_text = (
            "["
            + ", ".join(_unparse(param) for param in type_params)
            + "]"
        )

    signature = f"{node.name}{type_param_text}({', '.join(parts)})"

    if node.returns is not None:
        signature += f" -> {_unparse(node.returns)}"

    return signature


def get_function_kind(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    *,
    is_method: bool,
) -> str:
    """Classify a function's structural role."""
    if not is_method:
        return "function"

    decorator_names: set[str] = set()

    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Name):
            decorator_names.add(decorator.id)
        elif isinstance(decorator, ast.Attribute):
            decorator_names.add(decorator.attr)

    if "property" in decorator_names:
        return "property"

    if "classmethod" in decorator_names:
        return "classmethod"

    if "staticmethod" in decorator_names:
        return "staticmethod"

    return "method"


def build_function_info(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    *,
    is_method: bool = False,
) -> FunctionInfo:
    """Convert a function AST node into public index data."""
    return FunctionInfo(
        name=node.name,
        signature=build_signature(node),
        line=node.lineno,
        end_line=getattr(node, "end_lineno", node.lineno) or node.lineno,
        summary=get_summary(ast.get_docstring(node)),
        is_async=isinstance(node, ast.AsyncFunctionDef),
        kind=get_function_kind(node, is_method=is_method),
    )


def build_class_info(node: ast.ClassDef) -> ClassInfo:
    """Convert a top-level class AST node into public index data."""
    methods = [
        build_function_info(child, is_method=True)
        for child in node.body
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]

    return ClassInfo(
        name=node.name,
        line=node.lineno,
        end_line=getattr(node, "end_lineno", node.lineno) or node.lineno,
        bases=[_unparse(base) for base in node.bases],
        summary=get_summary(ast.get_docstring(node)),
        methods=methods,
    )


def read_source_file(filepath: Path) -> tuple[str | None, str | None]:
    """Read Python source using its declared encoding when possible."""
    try:
        with tokenize.open(filepath) as file:
            return file.read(), None
    except OSError as exc:
        return None, str(exc)
    except (UnicodeDecodeError, SyntaxError):
        pass

    last_error: Exception | None = None

    for encoding in ("utf-8-sig", "utf-8", "cp1252", "iso-8859-1"):
        try:
            return filepath.read_text(encoding=encoding), None
        except (UnicodeDecodeError, OSError) as exc:
            last_error = exc

    return (
        None,
        str(last_error) if last_error else "Unable to decode file",
    )


def analyze_file(
    filepath: Path,
    src_root: Path,
) -> tuple[ModuleInfo | None, IndexError | None]:
    """Analyze one Python file into structured module data."""
    rel_path = filepath.relative_to(src_root).as_posix()

    source, read_error = read_source_file(filepath)

    if source is None:
        return (
            None,
            IndexError(
                path=rel_path,
                error_type="read_error",
                message=read_error or "Unable to read file",
            ),
        )

    try:
        tree = ast.parse(source, filename=rel_path)
    except SyntaxError as exc:
        return (
            None,
            IndexError(
                path=rel_path,
                error_type="syntax_error",
                message=exc.msg,
                line=exc.lineno,
            ),
        )

    classes: list[ClassInfo] = []
    functions: list[FunctionInfo] = []

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            classes.append(build_class_info(node))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(build_function_info(node))

    return (
        ModuleInfo(
            path=rel_path,
            line_count=len(source.splitlines()),
            summary=get_summary(ast.get_docstring(tree)),
            classes=classes,
            functions=functions,
        ),
        None,
    )
