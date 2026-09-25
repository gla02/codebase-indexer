from __future__ import annotations

from pathlib import Path

from codebase_indexer.parser import analyze_file


def analyze(tmp_path: Path, source: str):
    path = tmp_path / "sample.py"
    path.write_text(source, encoding="utf-8")
    module, error = analyze_file(path, tmp_path)
    assert error is None
    assert module is not None
    return module


def test_module_class_and_function_metadata(tmp_path: Path) -> None:
    module = analyze(
        tmp_path,
        '''"""Module summary.\n\nMore detail.\n"""\n\nclass Runner(BaseRunner, Mixin):\n    """Runner summary."""\n\n    def run(self, value: int = 1) -> str:\n        """Run something."""\n        return str(value)\n\ndef helper(flag: bool = False) -> None:\n    """Helper summary."""\n''',
    )

    assert module.path == "sample.py"
    assert module.summary == "Module summary."
    assert len(module.classes) == 1
    assert len(module.functions) == 1

    cls = module.classes[0]
    assert cls.name == "Runner"
    assert cls.bases == ["BaseRunner", "Mixin"]
    assert cls.summary == "Runner summary."
    assert cls.methods[0].signature == "run(self, value: int = 1) -> str"
    assert cls.methods[0].kind == "method"

    fn = module.functions[0]
    assert fn.name == "helper"
    assert fn.signature == "helper(flag: bool = False) -> None"
    assert fn.kind == "function"


def test_signature_preserves_python_parameter_kinds(tmp_path: Path) -> None:
    module = analyze(
        tmp_path,
        '''def sample(a: int, /, b=2, *args: str, c: float = 3.5, **kwargs: bool) -> dict[str, int]:\n    pass\n''',
    )

    assert module.functions[0].signature == (
        "sample(a: int, /, b = 2, *args: str, c: float = 3.5, "
        "**kwargs: bool) -> dict[str, int]"
    )


def test_async_is_orthogonal_to_kind(tmp_path: Path) -> None:
    module = analyze(
        tmp_path,
        '''class Service:\n    @classmethod\n    async def create(cls):\n        pass\n\nasync def fetch():\n    pass\n''',
    )

    method = module.classes[0].methods[0]
    function = module.functions[0]

    assert method.kind == "classmethod"
    assert method.is_async is True
    assert function.kind == "function"
    assert function.is_async is True


def test_standard_member_kinds(tmp_path: Path) -> None:
    module = analyze(
        tmp_path,
        '''class Example:\n    def normal(self):\n        pass\n\n    @classmethod\n    def make(cls):\n        pass\n\n    @staticmethod\n    def utility():\n        pass\n\n    @property\n    def value(self):\n        return 1\n''',
    )

    kinds = {method.name: method.kind for method in module.classes[0].methods}
    assert kinds == {
        "normal": "method",
        "make": "classmethod",
        "utility": "staticmethod",
        "value": "property",
    }


def test_nested_definitions_are_not_promoted(tmp_path: Path) -> None:
    module = analyze(
        tmp_path,
        '''def outer():\n    def inner():\n        pass\n\nclass Outer:\n    class Nested:\n        pass\n\n    def method(self):\n        def local():\n            pass\n''',
    )

    assert [fn.name for fn in module.functions] == ["outer"]
    assert [cls.name for cls in module.classes] == ["Outer"]
    assert [method.name for method in module.classes[0].methods] == ["method"]


def test_syntax_error_is_structured(tmp_path: Path) -> None:
    path = tmp_path / "broken.py"
    path.write_text("def broken(:\n    pass\n", encoding="utf-8")

    module, error = analyze_file(path, tmp_path)

    assert module is None
    assert error is not None
    assert error.path == "broken.py"
    assert error.error_type == "syntax_error"
    assert error.line == 1


def test_empty_python_module_is_still_indexed(tmp_path: Path) -> None:
    module = analyze(tmp_path, "# intentionally empty\n")

    assert module.classes == []
    assert module.functions == []
    assert module.summary is None
