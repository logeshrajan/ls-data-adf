# ADF Environment Overrides

The deployment uses two nonsecret configuration files per environment:

- `<environment>.overrides.json` supplies generated ARM deployment parameters, including `factoryName`.
- `<environment>.template.overrides.json` handles exceptional artifact renames, properties that are not ARM parameters, and source-environment validation.

Keep ADF artifact names stable across environments whenever possible. An empty mapping means the exported name is deployed unchanged.

## Template Configuration

```json
{
  "artifactNameMappings": {
    "integrationRuntime": {
      "ir_dev": "ir_sit"
    },
    "linkedService": {
      "ls_keyvault_dev": "ls_keyvault_sit"
    }
  },
  "propertyOverrides": [
    {
      "resourceType": "Microsoft.DataFactory/factories/linkedServices",
      "resourceName": "ls_keyvault_sit",
      "path": "/properties/typeProperties/baseUrl",
      "value": "https://example-sit-kv.vault.azure.net/"
    }
  ],
  "forbiddenValues": [
    "example-dev-kv",
    "exampledevadls"
  ]
}
```

`artifactNameMappings` groups are descriptive and may cover deployable ADF artifacts such as `linkedService`, `dataset`, `pipeline`, `trigger`, `dataFlow`, and `credential`. An `integrationRuntime` mapping is also supported, but it updates references to an IR that must already exist in the target factory; it does not deploy the IR itself. A mapping updates matching references throughout the generated ARM template.

Each `propertyOverrides` entry selects exactly one ARM resource by `resourceType` and final ADF artifact name. `path` is an RFC 6901 JSON pointer relative to that resource. Set `required` to `false` only when an artifact is intentionally optional.

Use `forbiddenValues` for exact DEV-specific names, hostnames, URLs, or resource IDs that must not reach the target deployment. Do not put secrets in these files; use managed identity or Azure Key Vault references.

## ADF Environment Setup Prerequisites

Integration runtimes and managed private endpoints are outside this CI/CD deployment. Create and configure them through the separate ADF environment deployment setup before promoting ADF code.

- Keep the same IR name in every environment when possible.
- When an IR name differs, add an `integrationRuntime` mapping so linked-service `connectVia` references use the pre-created target IR.
- Create managed private endpoints for each target data resource and complete their approval before running dependent pipelines.
- CI/CD removes IR and managed-private-endpoint definitions, plus direct ARM dependencies on them, from the generated deployment payload.

The remaining ADF artifacts are deployed using ARM incremental mode. The workflow does not delete target artifacts that are absent from the template; cleanup is manual.