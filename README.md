# Codebase Indexer

A lightweight Python CLI for generating compact structural indexes of Python projects.

Codebase Indexer scans a project with Python's AST and produces two complementary views:

- `index.json` — structured, machine-readable information about modules, classes, methods, functions, signatures, docstrings, and source locations.
- `tree.txt` — a compact human-readable project tree with file-level structural summaries.

The tool is designed for fast codebase navigation, documentation, review, and AI-assisted development without requiring the project to be imported or executed.

## Why

Large Python projects can be difficult to understand quickly from filenames alone. Full source dumps are often too noisy, while simple directory trees omit the structure that matters.

Codebase Indexer keeps the useful middle layer:

```text
training/
├── data.py [2c / 8m / 18f] # DataSplit: Container for train/val/test splits...
├── labeling.py [2c / 3m] # LabelStrategy: Base class for training label-generation...
├── pipeline.py [4c / 2m / 18f] # TrainingCancelled: Raised when a training job...
└── tuning.py [6c / 22m / 30f] # TuningConfig: Configuration for hyperparameter tuning.
```

The JSON output retains richer detail for tools and deeper inspection.

## Installation

From the repository root:

```bash
pip install -e .
```

For development:

```bash
pip install -e ".[dev]"
```

## Quick start

Index the current directory:

```bash
codebase-index .
```

By default, output is written to:

```text
codebase-index/
├── index.json
└── tree.txt
```

`PATH` is optional, so this also works:

```bash
codebase-index
```

## CLI

```text
usage: codebase-index [-h] [-o OUTPUT] [--format {all,json,tree}]
                      [--exclude PATTERN] [--include-hidden]
                      [--no-default-excludes] [--no-gitignore]
                      [--version] [path]
```

### Common examples

Generate both outputs:

```bash
codebase-index .
```

Generate JSON only:

```bash
codebase-index ./src --format json
```

Write somewhere else:

```bash
codebase-index . --output ./docs/code-index
```

Add project-specific exclusions:

```bash
codebase-index . \
  --exclude runs \
  --exclude "tuning_results_*" \
  --exclude generated
```

Include hidden files and directories:

```bash
codebase-index . --include-hidden
```

Disable built-in exclusions:

```bash
codebase-index . --no-default-excludes
```

Ignore the project-root `.gitignore`:

```bash
codebase-index . --no-gitignore
```

## JSON schema

The canonical output is versioned:

```json
{
  "schema_version": "1.0",
  "project": {
    "name": "example-project",
    "root": "."
  },
  "modules": [],
  "errors": []
}
```

Each Python module records its project-relative path, line count, summary, classes, and top-level functions:

```json
{
  "path": "src/example/service.py",
  "line_count": 184,
  "summary": "Application service layer.",
  "classes": [],
  "functions": []
}
```

Classes include source locations, bases, summaries, and direct methods:

```json
{
  "name": "TrainingRunner",
  "line": 31,
  "end_line": 144,
  "bases": ["BaseRunner"],
  "summary": "Coordinates one training run.",
  "methods": []
}
```

Functions and methods preserve source-like signatures:

```json
{
  "name": "run_training",
  "signature": "run_training(config: TrainingConfig, *, verbose: bool = False) -> Result",
  "line": 72,
  "end_line": 118,
  "summary": "Run the configured training workflow.",
  "is_async": false,
  "kind": "function"
}
```

`kind` can currently be:

```text
function
method
classmethod
staticmethod
property
```

`is_async` is stored separately.

## What is indexed

Codebase Indexer currently extracts:

- module docstring summaries;
- top-level classes;
- direct class methods;
- top-level functions;
- async functions and methods;
- class base expressions;
- source line ranges;
- full source-like function signatures;
- standard `@classmethod`, `@staticmethod`, and `@property` classification.

Signatures preserve positional-only arguments, annotations, defaults, `*args`, keyword-only arguments, `**kwargs`, and return annotations where Python's AST exposes them.

The source code is parsed but never imported or executed.

## Project tree

`tree.txt` is intentionally compact. It is not a second copy of the JSON index.

For example:

```text
example-project
42 files shown
18 Python files indexed

├── src/
│   └── example/
│       ├── service.py [2c / 7m / 3f] # TrainingRunner: Coordinates one training run.
│       └── utils.py [5f] # normalize_path: Normalize a project-relative path.
├── tests/
│   └── test_service.py [1c / 8m] # TestTrainingRunner: Tests for TrainingRunner.
└── pyproject.toml # Python project config

Total indexed Python: 18 files, 9 classes, 31 methods, 47 functions
```

The principle is:

> Store richly, render selectively.

The JSON retains detailed structure; the tree stays useful for quick inspection.

## Exclusions

The scanner uses three layers of exclusions.

### Built-in exclusions

Common generated or dependency directories are ignored by default, including examples such as:

```text
.git
__pycache__
.pytest_cache
.mypy_cache
.ruff_cache
.venv
venv
node_modules
build
dist
```

Common binary, cache, model, archive, and large-data extensions are also excluded from the tree.

Use:

```bash
codebase-index . --no-default-excludes
```

to disable these built-in rules.

### `.gitignore`

If a `.gitignore` exists in the project root, its rules are applied by default.

This currently means the **project-root `.gitignore`**. Nested `.gitignore` files are not interpreted.

Disable this behavior with:

```bash
codebase-index . --no-gitignore
```

Git-style negation works according to normal parent-directory rules. For example:

```gitignore
generated/*
!generated/keep.py
```

can re-include `keep.py`, while:

```gitignore
generated/
!generated/keep.py
```

cannot re-include a file inside an already excluded parent directory.

### Custom exclusions

`--exclude` may be repeated:

```bash
codebase-index . \
  --exclude data \
  --exclude experiments \
  --exclude "runs_*"
```

Custom exclusions are matched against project-relative paths and path components.

## Hidden files

Most hidden files and directories are omitted by default.

A small set of useful project metadata remains visible, including files such as `.gitignore` and directories such as `.github`.

Use:

```bash
codebase-index . --include-hidden
```

to include other hidden paths. This does not disable built-in junk exclusions such as `.git`; combine it with `--no-default-excludes` if that is really desired.

## Error handling

A syntax error or unreadable Python file does not prevent the rest of the project from being indexed.

Errors are recorded explicitly:

```json
{
  "path": "src/legacy/broken.py",
  "error_type": "syntax_error",
  "message": "invalid syntax",
  "line": 42
}
```

Exit behavior:

- `0` — indexing completed and useful output was produced;
- `1` — fatal target/output error;
- `2` — invalid command-line usage, handled by `argparse`.

## Determinism and paths

Output ordering is deterministic.

Paths stored in generated files are project-relative and use `/` separators. Absolute host paths are not written into the index.

The output directory is automatically excluded from subsequent scans, preventing the tool from indexing its own generated files.

## Development

Install development dependencies:

```bash
pip install -e ".[dev]"
```

Run the test suite:

```bash
pytest
```

The current tests cover:

- regular and async functions;
- methods, classmethods, staticmethods, and properties;
- inheritance;
- source-like signatures;
- positional-only and keyword-only arguments;
- nested-definition behavior;
- module docstrings;
- syntax errors;
- empty modules;
- duplicate filenames in different directories;
- built-in and custom exclusions;
- hidden-path behavior;
- output self-exclusion;
- `.gitignore` behavior and negation;
- deterministic tree rendering;
- CLI help/version/error behavior;
- end-to-end index generation.

## Current scope

Codebase Indexer is deliberately focused on structural indexing.

Not currently included:

- import/dependency graphs;
- call graphs or caller/reference analysis;
- semantic analysis;
- complexity metrics;
- Git history analysis;
- embeddings or vector search;
- LLM integration;
- web UI;
- non-Python language parsing.

Some of these may make sense later, but they are not required for the core tool.

## Possible future additions

Ideas that fit the existing design without changing the core purpose include:

- optional base-class display in the tree;
- search/filtering over the generated index;
- compact hotspot reports based on existing structural data;
- additional renderers where they provide clear value.

Larger features such as dependency or caller analysis would require a separate design step.

## Design notes

A few choices are intentional:

- **AST instead of imports:** indexing should not execute project code.
- **Rich JSON + compact tree:** machine consumers and humans need different levels of detail.
- **Project-relative paths:** generated indexes should be portable and safe to share.
- **Non-fatal per-file errors:** one broken module should not make the whole codebase unreadable.
- **Minimal configuration:** useful defaults first; explicit CLI overrides when needed.
- **No filename-only mode:** preserving directory context avoids collisions between files with the same name.

## Status

`0.1.0` is an early public-facing release candidate. The core behavior has been exercised against a substantial real-world Python project and is protected by an automated test suite.

The public schema is currently `1.0`.


## License

Codebase Indexer is released under the MIT License. See [`LICENSE`](LICENSE).
