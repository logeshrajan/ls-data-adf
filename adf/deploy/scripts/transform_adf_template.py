"""Apply environment-specific mappings and property overrides to an ADF ARM template.

Configuration format:
{
  "artifactNameMappings": {
    "integrationRuntime": {"ir_dev": "ir_sit"},
    "linkedService": {"ls_keyvault_dev": "ls_keyvault"}
  },
  "propertyOverrides": [
    {
      "resourceType": "Microsoft.DataFactory/factories/linkedServices",
      "resourceName": "ls_keyvault",
      "path": "/properties/typeProperties/baseUrl",
      "value": "https://example-sit-kv.vault.azure.net/"
    }
  ],
  "forbiddenValues": ["example-dev-kv", "exampledevstorage"]
}

Artifact mappings are optional. Stable names require no mapping. A mapping updates
the resource name and matching references throughout the ARM template. Property
paths are RFC 6901 JSON pointers relative to the matching ARM resource.

Integration runtime and managed private endpoint resources are removed from the
deployment payload. They must be provisioned by the ADF environment setup.
"""

import json
import re
import sys
from typing import Any


EXCLUDED_RESOURCE_TYPES = {
    "Microsoft.DataFactory/factories/integrationRuntimes",
    "Microsoft.DataFactory/factories/managedVirtualNetworks/managedPrivateEndpoints",
}

EXCLUDED_DEPENDENCY_MARKERS = (
    "Microsoft.DataFactory/factories/integrationRuntimes",
    "Microsoft.DataFactory/factories/managedVirtualNetworks/managedPrivateEndpoints",
    "/integrationRuntimes/",
    "/managedPrivateEndpoints/",
)


def _load_json(path: str) -> Any:
    with open(path, encoding="utf-8-sig") as file:
        return json.load(file)


def _replace_name(value: str, source: str, target: str) -> str:
    boundary = r"A-Za-z0-9_.-"
    return re.sub(
        rf"(?<![{boundary}]){re.escape(source)}(?![{boundary}])",
        lambda _: target,
        value,
    )


def _replace_names(node: Any, mappings: dict[str, str]) -> Any:
    if isinstance(node, dict):
        return {key: _replace_names(value, mappings) for key, value in node.items()}
    if isinstance(node, list):
        return [_replace_names(value, mappings) for value in node]
    if isinstance(node, str):
        for source, target in mappings.items():
            node = _replace_name(node, source, target)
        return node
    return node


def _artifact_name(resource_name: Any) -> str:
    if not isinstance(resource_name, str):
        return ""

    literal_suffixes = re.findall(r"/([^/'\"]+)(?=['\"])", resource_name)
    if literal_suffixes:
        return literal_suffixes[-1]

    return resource_name.rstrip("/").rsplit("/", 1)[-1]


def _set_pointer(document: Any, pointer: str, value: Any) -> None:
    if not pointer.startswith("/"):
        raise ValueError(f"Property path must start with '/': {pointer!r}")

    tokens = [
        token.replace("~1", "/").replace("~0", "~")
        for token in pointer.split("/")[1:]
    ]
    if not tokens:
        raise ValueError("Property path must not target the resource root.")

    parent = document
    for token in tokens[:-1]:
        parent = parent[int(token)] if isinstance(parent, list) else parent[token]

    last = int(tokens[-1]) if isinstance(parent, list) else tokens[-1]
    parent[last] = value


def _collect_mappings(configuration: dict[str, Any]) -> dict[str, str]:
    groups = configuration.get("artifactNameMappings", {})
    if not isinstance(groups, dict):
        raise ValueError("artifactNameMappings must be an object.")

    mappings: dict[str, str] = {}
    for artifact_type, entries in groups.items():
        if not isinstance(entries, dict):
            raise ValueError(
                f"artifactNameMappings.{artifact_type} must be an object."
            )
        for source, target in entries.items():
            if not isinstance(source, str) or not isinstance(target, str):
                raise ValueError("Artifact mapping names must be strings.")
            if source in mappings and mappings[source] != target:
                raise ValueError(f"Conflicting mappings for artifact {source!r}.")
            mappings[source] = target
    return mappings


def _exclude_setup_resources(resources: list[Any]) -> list[Any]:
    retained = [
        resource
        for resource in resources
        if not isinstance(resource, dict)
        or resource.get("type") not in EXCLUDED_RESOURCE_TYPES
    ]

    for resource in retained:
        if not isinstance(resource, dict) or not isinstance(resource.get("dependsOn"), list):
            continue
        resource["dependsOn"] = [
            dependency
            for dependency in resource["dependsOn"]
            if not (
                isinstance(dependency, str)
                and any(marker in dependency for marker in EXCLUDED_DEPENDENCY_MARKERS)
            )
        ]

    return retained


def transform(template: Any, configuration: dict[str, Any]) -> Any:
    mappings = _collect_mappings(configuration)
    transformed = _replace_names(template, mappings)

    resources = transformed.get("resources", [])
    if not isinstance(resources, list):
        raise ValueError("ARM template resources must be an array.")

    overrides = configuration.get("propertyOverrides", [])
    if not isinstance(overrides, list):
        raise ValueError("propertyOverrides must be an array.")

    for override in overrides:
        if not isinstance(override, dict):
            raise ValueError("Each property override must be an object.")
        resource_type = override.get("resourceType")
        resource_name = override.get("resourceName")
        path = override.get("path")
        if not all(isinstance(item, str) for item in (resource_type, resource_name, path)):
            raise ValueError(
                "Each property override requires string resourceType, resourceName, and path."
            )
        if "value" not in override:
            raise ValueError(f"Property override {resource_name}:{path} requires value.")

        matches = [
            resource
            for resource in resources
            if resource.get("type") == resource_type
            and _artifact_name(resource.get("name")) == resource_name
        ]
        required = override.get("required", True)
        if len(matches) != 1:
            message = (
                f"Property override expected one resource but found {len(matches)}: "
                f"{resource_type}/{resource_name}"
            )
            if required:
                raise ValueError(message)
            print(f"Warning: {message}; optional override skipped.")
            continue

        try:
            _set_pointer(matches[0], path, override["value"])
        except (KeyError, IndexError, TypeError, ValueError) as error:
            if required:
                raise ValueError(
                    f"Property path did not resolve for {resource_name}: {path}"
                ) from error
            print(
                f"Warning: property path did not resolve for {resource_name}: "
                f"{path}; optional override skipped."
            )
            continue
        print(f"ADF property override applied: {resource_type}/{resource_name}{path}")

    transformed["resources"] = _exclude_setup_resources(resources)

    serialized = json.dumps(transformed)
    forbidden_values = configuration.get("forbiddenValues", [])
    if not isinstance(forbidden_values, list) or not all(
        isinstance(value, str) for value in forbidden_values
    ):
        raise ValueError("forbiddenValues must be an array of strings.")
    found = [value for value in forbidden_values if value and value in serialized]
    if found:
        raise ValueError(
            "Forbidden source-environment value(s) remain in ARM template: "
            + ", ".join(found)
        )

    return transformed


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "Usage: python3 transform_adf_template.py "
            "<arm-template.json> <environment-config.json>"
        )
        return 1

    try:
        template = _load_json(sys.argv[1])
        configuration = _load_json(sys.argv[2])
        if not isinstance(template, dict) or not isinstance(configuration, dict):
            raise ValueError("Template and environment configuration must be objects.")
        transformed = transform(template, configuration)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"ERROR: {error}")
        return 1

    with open(sys.argv[1], "w", encoding="utf-8") as file:
        json.dump(transformed, file, indent=2)
        file.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())