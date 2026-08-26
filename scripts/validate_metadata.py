#!/usr/bin/env python3
"""Validate issue metadata blocks against local JSON Schemas.

This script expects a YAML frontmatter block at the top of a markdown file.
It keeps dependencies to the standard library so it can run in GitHub Actions
without extra packaging.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Tuple


def _parse_scalar(value: str) -> Any:
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if re.fullmatch(r"-?\d+\.\d+", value):
        return float(value)
    return value


def parse_frontmatter(text: str) -> Tuple[Dict[str, Any], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text

    end = 1
    while end < len(lines) and lines[end].strip() != "---":
        end += 1

    if end >= len(lines):
        raise ValueError("missing closing frontmatter marker")

    block = lines[1:end]
    body = "\n".join(lines[end + 1 :])
    data: Dict[str, Any] = {}
    current_key = None
    current_item = None
    for raw in block:
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue

        if line.startswith("    ") and current_item is not None and ":" in line:
            key, value = line.strip().split(":", 1)
            current_item[key.strip()] = _parse_scalar(value.strip())
            continue

        if line.startswith("  - ") and current_key:
            rest = line[4:].strip()
            target = data.setdefault(current_key, [])
            if rest and ":" in rest:
                key, value = rest.split(":", 1)
                current_item = {key.strip(): _parse_scalar(value.strip())}
                target.append(current_item)
            else:
                current_item = None
                target.append(rest)
            continue

        current_item = None
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            current_key = key
            if value == "":
                data[key] = []
            else:
                data[key] = _parse_scalar(value)
        else:
            raise ValueError(f"unsupported frontmatter line: {line}")

    return data, body


def validate_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> None:
    required = schema.get("required", [])
    for key in required:
        if key not in data:
            raise ValueError(f"missing required key: {key}")

    props = schema.get("properties", {})
    for key, spec in props.items():
        if key not in data:
            continue
        value = data[key]
        if "const" in spec and value != spec["const"]:
            raise ValueError(f"{key} must be {spec['const']!r}")
        if "enum" in spec and value not in spec["enum"]:
            raise ValueError(f"{key} must be one of {spec['enum']!r}")
        if spec.get("type") == "integer" and not isinstance(value, int):
            raise ValueError(f"{key} must be integer")
        if spec.get("type") == "number" and not isinstance(value, (int, float)):
            raise ValueError(f"{key} must be number")
        if spec.get("type") == "string" and not isinstance(value, str):
            raise ValueError(f"{key} must be string")
        if spec.get("type") == "boolean" and not isinstance(value, bool):
            raise ValueError(f"{key} must be boolean")
        if spec.get("type") == "array" and not isinstance(value, list):
            raise ValueError(f"{key} must be array")


def load_schema(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema", required=True)
    parser.add_argument("file")
    args = parser.parse_args()

    schema_path = Path(args.schema)
    file_path = Path(args.file)
    schema = load_schema(schema_path)
    metadata, _ = parse_frontmatter(file_path.read_text(encoding="utf-8"))
    validate_schema(metadata, schema)
    print(f"OK: {file_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
