# ADF Override References

This folder contains the environment override files used by the ADF deployment workflows.

## Purpose
The JSON files in this folder are used to rewrite resource names, linked service values, trigger scopes, and integration runtime mappings for the selected deployment environment.

## Why There Are 2 File Types

The files are split because they serve two different deployment layers:

- `*.overrides.json` is for runtime values that need to be substituted when the ADF deployment parameters are prepared.
- `*.template.overrides.json` is for template-level name rewrites that must happen in the exported ARM template before deployment.

Keeping them separate makes it easier to manage values that belong to the deployment payload versus values that belong to the template itself.

## Files

- [sit.overrides.json](sit.overrides.json)
- [sit.template.overrides.json](sit.template.overrides.json)
- [uat.overrides.json](uat.overrides.json)
- [uat.template.overrides.json](uat.template.overrides.json)
- [prod.overrides.json](prod.overrides.json)
- [prod.template.overrides.json](prod.template.overrides.json)
- [dr.overrides.json](dr.overrides.json)
- [dr.template.overrides.json](dr.template.overrides.json)

## File Types

- `*.overrides.json` files contain runtime overrides such as factory names, linked service values, and trigger scopes.
- `*.template.overrides.json` files contain template-level name mappings such as integration runtime and storage account rewrites.

## Where These Values Are Replaced

- `*.overrides.json` values are applied in the deployment parameters and runtime deployment payload for the target environment.
- `*.template.overrides.json` values are applied in the exported ARM template before the template is deployed.
- In practice, these values replace source-environment references with target-environment values before the deployment is sent to Azure.

## Files Affected During Deployment

- The exported ARM template is rewritten with template override values.
- The deployment parameters file is updated with runtime override values.
- Any generated deployment payloads that depend on those values will use the rewritten target-environment names and scopes.

## Example Reference

Use the UAT files as a reference example:

- [uat.overrides.json](uat.overrides.json)
- [uat.template.overrides.json](uat.template.overrides.json)

### Runtime Override Example

- `factoryName`: `ls-uat-adf`
  - Target ADF factory name for the selected environment.

- `ls_keyvault_properties_typeProperties_baseUrl`: `https://mbb-kv-data-uat-myw-01.vault.azure.net/`
  - Key Vault base URL used by the Key Vault linked service.

- `ls_sqldb_config_properties_typeProperties_server`: `mbb-sql-data-uat-myw-01.database.windows.net`
  - SQL server used by the SQL DB config linked service.

- `ls_sqldb_config_properties_typeProperties_database`: `mbb-sqldb-data-uat-myw-01`
  - SQL database name used by the SQL DB config linked service.

- `TRG_NEW_AEA_FILE_properties_typeProperties_scope`: `/subscriptions/7b791bb0-d1f4-4b81-bea9-ee0629690f4a/resourceGroups/mbb-rg-datastorage-uat-myw-01/providers/Microsoft.Storage/storageAccounts/mbbsaadlsdatauatmyw01`
  - Storage account scope used by the `TRG_NEW_AEA_FILE` trigger.

- `TRG_CFS_FILE_INGESTION_properties_typeProperties_scope`: `/subscriptions/7b791bb0-d1f4-4b81-bea9-ee0629690f4a/resourceGroups/mbb-rg-datastorage-uat-myw-01/providers/Microsoft.Storage/storageAccounts/mbbsaadlsdatauatmyw01`
  - Storage account scope used by the `TRG_CFS_FILE_INGESTION` trigger.

### Template Override Example

- `mbb-selfhosted-ir-data-dev-myw-01`: `mbb-selfhosted-ir-data-uat-myw-01`
  - Maps the self-hosted integration runtime name from the source environment to the target environment.

- `mbb-azure-ir-data-dev-myw-01`: `mbb-azure-ir-data-uat-myw-01`
  - Maps the first Azure integration runtime name from the source environment to the target environment.

- `mbb-azure-ir-data-dev-myw-02`: `mbb-azure-ir-data-uat-myw-02`
  - Maps the second Azure integration runtime name from the source environment to the target environment.

- `mbbsaadlsdatadevmyw01`: `mbbsaadlsdatauatmyw01`
  - Maps the source storage account name to the target storage account name.

## Notes

- Make sure the required resources already exist in the target environment, such as Key Vault, storage accounts, and self-hosted integration runtime.
- These values are environment-specific and should match the selected deployment infrastructure.
- Update this README whenever files in this folder are added, removed, or renamed.