#!/usr/bin/env python3
"""Zero-dependency run-artifact validator (JSON-Schema draft-07 subset).

Usage:
  validate-run-artifact.py <schema.json> <artifact.json>
  validate-run-artifact.py <schema.json> <ledger.jsonl>   # validates per line

Why this exists: a malformed run artifact should surface as a deterministic,
named-field fix instruction — never as a model-judged retry round. The
sdlc-pipeline skill runs this after writing and before gating (see SKILL.md
§ "Artifact shape validation"); it uses only the stdlib so host projects need
no installs.

Supported keywords (the subset the schemas under references/schemas/ use):
type (incl. union lists), required, properties, additionalProperties (bool or
schema), items, enum, const, pattern, minimum, maximum, minItems, maxLength.

Exit codes: 0 valid · 1 invalid (one line per error) · 2 usage/IO error.
"""
from __future__ import annotations

import json
import re
import sys

TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
    "null": type(None),
}


def type_ok(value, name: str) -> bool:
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    py = TYPES.get(name)
    if py is dict or py is list or py is str:
        return isinstance(value, py)
    if py is bool:
        return isinstance(value, bool)
    if py is type(None):
        return value is None
    return False


def validate(value, schema: dict, path: str, errors: list[str]) -> None:
    if "const" in schema and value != schema["const"]:
        errors.append("%s: expected const %r, got %r" % (path, schema["const"], value))
        return
    if "enum" in schema and value not in schema["enum"]:
        errors.append("%s: %r not in enum %r" % (path, value, schema["enum"]))
        return
    t = schema.get("type")
    if t is not None:
        names = t if isinstance(t, list) else [t]
        if not any(type_ok(value, n) for n in names):
            errors.append("%s: expected type %s, got %s" % (path, "|".join(names), type(value).__name__))
            return
    if isinstance(value, str):
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append("%s: %r does not match pattern %r" % (path, value[:60], schema["pattern"]))
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.append("%s: string longer than maxLength %d" % (path, schema["maxLength"]))
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append("%s: %s below minimum %s" % (path, value, schema["minimum"]))
        if "maximum" in schema and value > schema["maximum"]:
            errors.append("%s: %s above maximum %s" % (path, value, schema["maximum"]))
    if isinstance(value, dict):
        for req in schema.get("required", []):
            if req not in value:
                errors.append("%s: missing required field %r" % (path, req))
        props = schema.get("properties", {})
        extra = schema.get("additionalProperties", True)
        for key, sub in value.items():
            if key in props:
                validate(sub, props[key], "%s.%s" % (path, key), errors)
            elif isinstance(extra, dict):
                validate(sub, extra, "%s.%s" % (path, key), errors)
            elif extra is False:
                errors.append("%s: unexpected field %r" % (path, key))
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append("%s: fewer than minItems %d" % (path, schema["minItems"]))
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for i, item in enumerate(value):
                validate(item, item_schema, "%s[%d]" % (path, i), errors)


def validate_document(doc, schema: dict) -> list[str]:
    errors: list[str] = []
    validate(doc, schema, "$", errors)
    return errors


def main() -> None:
    if len(sys.argv) != 3:
        sys.stderr.write(__doc__.strip() + "\n")
        sys.exit(2)
    schema_path, artifact_path = sys.argv[1], sys.argv[2]
    try:
        with open(schema_path, encoding="utf-8") as fh:
            schema = json.load(fh)
        with open(artifact_path, encoding="utf-8") as fh:
            raw = fh.read()
    except (OSError, json.JSONDecodeError) as e:
        sys.stderr.write("validate-run-artifact: %s\n" % e)
        sys.exit(2)

    failures = 0
    if artifact_path.endswith(".jsonl"):
        for n, line in enumerate(raw.splitlines(), 1):
            if not line.strip():
                continue
            try:
                doc = json.loads(line)
            except json.JSONDecodeError as e:
                print("%s:%d: unparseable JSON line: %s" % (artifact_path, n, e))
                failures += 1
                continue
            for err in validate_document(doc, schema):
                print("%s:%d: %s" % (artifact_path, n, err))
                failures += 1
    else:
        try:
            doc = json.loads(raw)
        except json.JSONDecodeError as e:
            print("%s: unparseable JSON: %s" % (artifact_path, e))
            sys.exit(1)
        for err in validate_document(doc, schema):
            print("%s: %s" % (artifact_path, err))
            failures += 1

    if failures:
        print("INVALID: %d error(s) against %s" % (failures, schema_path))
        sys.exit(1)
    print("ok: %s conforms to %s" % (artifact_path, schema_path))
    sys.exit(0)


if __name__ == "__main__":
    main()
