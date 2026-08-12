"""
validate_arm_json.py
Validates that one or more ARM JSON files are well-formed objects.
Exits non-zero if any file is missing, not valid JSON, or not a JSON object.

Usage:
    python3 validate_arm_json.py <file1> [file2 ...]
"""
import json
import pathlib
import sys


def validate(path_str: str) -> None:
    path = pathlib.Path(path_str)
    if not path.exists():
        print(f"ERROR: File not found: {path_str}")
        sys.exit(1)

    text = path.read_text(encoding="utf-8")
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        print(f"ERROR: {path_str} is not valid JSON: {exc}")
        sys.exit(1)

    # Guard against accidentally double-serialised payloads.
    if isinstance(obj, str):
        try:
            obj = json.loads(obj)
            path.write_text(json.dumps(obj, indent=2), encoding="utf-8")
            print(f"INFO:  {path_str} was a stringified JSON object — normalised.")
        except json.JSONDecodeError:
            print(f"ERROR: {path_str} is a plain string, not a JSON object.")
            sys.exit(1)

    if not isinstance(obj, dict):
        print(f"ERROR: {path_str} top-level type is {type(obj).__name__}, expected object.")
        sys.exit(1)

    print(f"OK:    {path_str} is a valid JSON object.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 validate_arm_json.py <file1> [file2 ...]")
        sys.exit(1)
    for arg in sys.argv[1:]:
        validate(arg)
