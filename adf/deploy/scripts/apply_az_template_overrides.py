"""
Apply overrides to an ARM template JSON file.

Use this for values that are NOT exposed as ARM template parameters
(e.g. credential resourceId baked into Microsoft.DataFactory/factories/credentials).

Two input formats are supported:

1. Legacy (simple string find/replace, case-sensitive, required):
   {
     "<exact string to find>": "<replacement string>",
     ...
   }

2. Structured (list of override entries):
   [
     { "find": "<text>", "replace": "<text>",
       "caseInsensitive": false, "required": true },
     { "regex": "<python regex>", "replace": "<text>",
       "caseInsensitive": false, "required": true },
     { "jsonPointer": "/resources/0/properties/typeProperties/resourceId",
       "value": "<any json value>", "required": true }
   ]

   - "caseInsensitive": defaults to false. Valid with "find" or "regex".
   - "required": defaults to true. When false, a missing match is logged
     and skipped instead of failing.
   - Exactly one of "find", "regex", or "jsonPointer" must be present.

Behavior:
- find/regex overrides operate on the serialized template text.
- jsonPointer overrides operate on the parsed JSON object.
- After all overrides are applied, the result must still parse as JSON.

Usage:
  python3 apply_az_template_overrides.py <arm-template.json> <template-overrides.json>
"""

import json
import re
import sys
from typing import Any, List, Tuple, Union


def _coerce_to_entries(raw: Any) -> List[dict]:
    """Normalize legacy dict[str, str] to list of structured entries."""
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        entries: List[dict] = []
        for find_str, replace_str in raw.items():
            if not isinstance(find_str, str) or not isinstance(replace_str, str):
                raise ValueError(
                    f"Legacy override entries must be string -> string: {find_str!r}"
                )
            entries.append({"find": find_str, "replace": replace_str})
        return entries
    raise ValueError("Overrides file must be a JSON object or array.")


def _resolve_pointer(doc: Any, pointer: str) -> Tuple[Any, Union[str, int]]:
    """
    Walk a JSON pointer (RFC 6901) and return (parent_container, last_token).
    The caller can then write parent_container[last_token] = value.
    """
    if not pointer.startswith("/"):
        raise ValueError(f"JSON pointer must start with '/': {pointer!r}")

    tokens = [
        t.replace("~1", "/").replace("~0", "~")
        for t in pointer.split("/")[1:]
    ]
    if not tokens:
        raise ValueError("JSON pointer must reference a child, not the root.")

    parent = doc
    for token in tokens[:-1]:
        if isinstance(parent, list):
            parent = parent[int(token)]
        else:
            parent = parent[token]

    last = tokens[-1]
    if isinstance(parent, list):
        return parent, int(last)
    return parent, last


def _apply_text_override(text: str, entry: dict) -> Tuple[str, bool]:
    """Apply a single string- or regex-based override. Returns (new_text, matched)."""
    replace_str = entry.get("replace")
    if not isinstance(replace_str, str):
        raise ValueError(f"Override 'replace' must be a string: {entry}")

    case_insensitive = bool(entry.get("caseInsensitive", False))

    if "find" in entry:
        find_str = entry["find"]
        if not isinstance(find_str, str):
            raise ValueError(f"Override 'find' must be a string: {entry}")
        flags = re.IGNORECASE if case_insensitive else 0
        pattern = re.compile(re.escape(find_str), flags)
        new_text, count = pattern.subn(replace_str, text)
        matched = count > 0
        if matched:
            print(
                f"Template override applied ({count} occurrence(s)): "
                f"{find_str} -> {replace_str}"
            )
        return new_text, matched

    if "regex" in entry:
        pattern_str = entry["regex"]
        if not isinstance(pattern_str, str):
            raise ValueError(f"Override 'regex' must be a string: {entry}")
        flags = re.IGNORECASE if case_insensitive else 0
        pattern = re.compile(pattern_str, flags)
        new_text, count = pattern.subn(replace_str, text)
        matched = count > 0
        if matched:
            print(
                f"Template regex override applied ({count} match(es)): "
                f"/{pattern_str}/ -> {replace_str}"
            )
        return new_text, matched

    raise ValueError(f"Text override must have 'find' or 'regex': {entry}")


def _apply_pointer_override(doc: Any, entry: dict) -> bool:
    """Apply a JSON-pointer override in place. Returns True if applied."""
    pointer = entry["jsonPointer"]
    if not isinstance(pointer, str):
        raise ValueError(f"Override 'jsonPointer' must be a string: {entry}")
    if "value" not in entry:
        raise ValueError(f"Override with 'jsonPointer' must include 'value': {entry}")

    try:
        parent, last = _resolve_pointer(doc, pointer)
        parent[last] = entry["value"]
    except (KeyError, IndexError, TypeError, ValueError):
        return False

    print(f"Template pointer override applied: {pointer} = {entry['value']!r}")
    return True


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "Usage: python3 apply_az_template_overrides.py "
            "<arm-template.json> <template-overrides.json>"
        )
        return 1

    template_path = sys.argv[1]
    overrides_path = sys.argv[2]

    with open(template_path, encoding="utf-8") as f:
        template_text = f.read()

    with open(overrides_path, encoding="utf-8-sig") as f:
        raw_overrides = json.load(f)

    try:
        entries = _coerce_to_entries(raw_overrides)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1

    text_entries = [e for e in entries if "find" in e or "regex" in e]
    pointer_entries = [e for e in entries if "jsonPointer" in e]

    # Phase 1: apply text-based overrides on serialized template.
    for entry in text_entries:
        try:
            template_text, matched = _apply_text_override(template_text, entry)
        except ValueError as exc:
            print(f"ERROR: {exc}")
            return 1
        if not matched:
            target = entry.get("find") or entry.get("regex")
            if entry.get("required", True):
                print(f"ERROR: Required override did not match: {target}")
                return 1
            print(f"Warning: Optional override did not match (skipped): {target}")

    # Phase 2: parse and apply pointer-based overrides on the JSON object.
    try:
        doc = json.loads(template_text)
    except json.JSONDecodeError as exc:
        print(f"ERROR: Template is no longer valid JSON after text overrides: {exc}")
        return 1

    for entry in pointer_entries:
        try:
            applied = _apply_pointer_override(doc, entry)
        except ValueError as exc:
            print(f"ERROR: {exc}")
            return 1
        if not applied:
            pointer = entry.get("jsonPointer")
            if entry.get("required", True):
                print(f"ERROR: Required pointer override did not resolve: {pointer}")
                return 1
            print(f"Warning: Optional pointer override did not resolve (skipped): {pointer}")

    if pointer_entries:
        template_text = json.dumps(doc, indent=2)

    # Final sanity check.
    try:
        json.loads(template_text)
    except json.JSONDecodeError as exc:
        print(f"ERROR: Template is no longer valid JSON after overrides: {exc}")
        return 1

    with open(template_path, "w", encoding="utf-8") as f:
        f.write(template_text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
