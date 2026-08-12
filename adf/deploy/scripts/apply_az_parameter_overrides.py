"""
Apply key/value overrides to an Azure CLI parameters JSON file.

Input/output format:
{
  "paramName": {"value": "..."}
}

Usage:
  python3 apply_az_parameter_overrides.py <az-parameters.json> <overrides.json>
"""

import json
import sys


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python3 apply_az_parameter_overrides.py <az-parameters.json> <overrides.json>")
        return 1

    az_params_path = sys.argv[1]
    overrides_path = sys.argv[2]

    with open(az_params_path, encoding="utf-8") as f:
        az_params = json.load(f)

    with open(overrides_path, encoding="utf-8") as f:
        overrides = json.load(f)

    if not isinstance(az_params, dict):
        print(f"ERROR: Invalid Azure parameters file (expected object): {az_params_path}")
        return 1

    if not isinstance(overrides, dict):
        print(f"ERROR: Overrides file must be a JSON object: {overrides_path}")
        return 1

    for key, value in overrides.items():
        slot = az_params.get(key)
        if not isinstance(slot, dict):
            slot = {}
            az_params[key] = slot
        slot["value"] = value
        print(f"Override applied to deployment file: {key}={value}")

    with open(az_params_path, "w", encoding="utf-8") as f:
        json.dump(az_params, f, indent=2)
        f.write("\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
