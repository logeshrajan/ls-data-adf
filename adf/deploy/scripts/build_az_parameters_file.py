"""
Build an Azure CLI-compatible parameters JSON file from an ARM deploymentParameters file.

Input format (deploymentParameters schema):
{
  "$schema": "...",
  "contentVersion": "...",
  "parameters": {
    "name": {"value": "..."}
  }
}

Output format (az deployment --parameters @file):
{
  "name": {"value": "..."}
}
"""

import json
import sys


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python3 build_az_parameters_file.py <input-parameters.json> <output-parameters.json>")
        return 1

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    with open(input_path, encoding="utf-8") as f:
        doc = json.load(f)

    params = doc.get("parameters")
    if not isinstance(params, dict):
        print(f"ERROR: Invalid deploymentParameters file (missing object 'parameters'): {input_path}")
        return 1

    az_params = {}
    for key, meta in params.items():
        if isinstance(meta, dict) and "value" in meta:
            az_params[key] = {"value": meta["value"]}

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(az_params, f, indent=2)
        f.write("\n")

    print(f"Wrote Azure CLI parameters file: {output_path}")
    print(f"Parameter count: {len(az_params)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
