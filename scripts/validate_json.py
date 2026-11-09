#!/usr/bin/env python3
"""Validate repository JSON files and PrairieLearn metadata schemas."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from jsonschema import FormatChecker, SchemaError
from jsonschema.validators import validator_for

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIRECTORY = REPOSITORY_ROOT / ".prairielearn" / "schemas"
EXCLUDED_DIRECTORIES = {".git", ".venv", "node_modules"}
# VS Code always treats settings.json as JSON with Comments, despite its suffix.
EXCLUDED_FILES = {REPOSITORY_ROOT / ".vscode" / "settings.json"}


def reject_nonstandard_constant(value: str) -> None:
    """Reject Infinity and NaN, which Python accepts but JSON does not."""
    raise ValueError(f"{value} is not a valid JSON value")


def load_json(path: Path) -> Any:
    """Load strict UTF-8 JSON from *path*."""
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=reject_nonstandard_constant,
    )


def find_json_files(inputs: Sequence[Path]) -> tuple[list[Path], list[str]]:
    """Return JSON files found beneath input files and directories."""
    files: set[Path] = set()
    errors: list[str] = []

    for input_path in inputs:
        path = input_path.resolve()
        if not path.exists():
            errors.append(f"{input_path}: path does not exist")
            continue
        if path.is_file():
            if path.suffix != ".json":
                errors.append(f"{input_path}: expected a .json file")
            else:
                files.add(path)
            continue

        for candidate in path.rglob("*.json"):
            if any(part in EXCLUDED_DIRECTORIES for part in candidate.parts):
                continue
            resolved = candidate.resolve()
            if resolved not in EXCLUDED_FILES:
                files.add(resolved)

    return sorted(files), errors


def schema_name_for(path: Path) -> str | None:
    """Return the PrairieLearn schema corresponding to *path*, if any."""
    try:
        relative = path.relative_to(REPOSITORY_ROOT)
    except ValueError:
        return None

    parts = relative.parts
    if relative == Path("infoCourse.json"):
        return "infoCourse.json"
    if parts[0] == "courseInstances" and path.name == "infoCourseInstance.json":
        return "infoCourseInstance.json"
    if parts[0] == "courseInstances" and path.name == "infoAssessment.json":
        return "infoAssessment.json"
    if parts[0] == "questions" and path.name == "info.json":
        return "infoQuestion.json"
    if len(parts) == 3 and parts[0] == "elements" and path.name == "info.json":
        return "infoElementCourse.json"
    if len(parts) == 3 and parts[0] == "elementExtensions" and path.name == "info.json":
        return "infoElementExtension.json"
    return None


def json_path(parts: Iterable[str | int]) -> str:
    """Format a jsonschema error path for human-readable output."""
    result = "$"
    for part in parts:
        if isinstance(part, int):
            result += f"[{part}]"
        elif part.isidentifier():
            result += f".{part}"
        else:
            result += f"[{part!r}]"
    return result


def display_path(path: Path) -> Path:
    try:
        return path.relative_to(REPOSITORY_ROOT)
    except ValueError:
        return path


def validate_files(paths: Sequence[Path]) -> tuple[int, int, list[str]]:
    """Validate paths, returning file count, schema count, and errors."""
    schema_cache: dict[str, Any] = {}
    schema_count = 0
    errors: list[str] = []

    for path in paths:
        shown_path = display_path(path)
        try:
            instance = load_json(path)
        except json.JSONDecodeError as exc:
            errors.append(
                f"{shown_path}:{exc.lineno}:{exc.colno}: invalid JSON: {exc.msg}"
            )
            continue
        except (OSError, UnicodeError, ValueError) as exc:
            errors.append(f"{shown_path}: invalid JSON: {exc}")
            continue

        schema_name = schema_name_for(path)
        if schema_name is None:
            continue
        schema_count += 1

        schema_path = SCHEMA_DIRECTORY / schema_name
        try:
            if schema_name not in schema_cache:
                schema_cache[schema_name] = load_json(schema_path)
            schema = schema_cache[schema_name]
            validator_class = validator_for(schema)
            validator_class.check_schema(schema)
            validation_errors = sorted(
                validator_class(schema, format_checker=FormatChecker()).iter_errors(
                    instance
                ),
                key=lambda error: [str(part) for part in error.absolute_path],
            )
        except (OSError, UnicodeError, ValueError, SchemaError) as exc:
            errors.append(f"{schema_path}: unable to load schema: {exc}")
            continue

        errors.extend(
            f"{shown_path}:{json_path(error.absolute_path)}: {error.message}"
            for error in validation_errors
        )

    return len(paths), schema_count, errors


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate strict JSON syntax and apply PrairieLearn schemas to recognized "
            "course metadata files."
        )
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="files or directories to validate (defaults to the repository)",
    )
    args = parser.parse_args(argv)

    inputs = args.paths or [REPOSITORY_ROOT]
    files, errors = find_json_files(inputs)
    file_count, schema_count, validation_errors = validate_files(files)
    errors.extend(validation_errors)

    if errors:
        print("JSON validation failed:", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        return 1

    print(
        f"Validated {file_count} JSON files "
        f"({schema_count} against PrairieLearn schemas)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
