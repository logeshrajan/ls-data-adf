# Reusable Azure Data Factory CI/CD

This repository validates Azure Data Factory resources from pull requests and promotes one immutable ARM artifact through SIT, UAT, and PROD with GitHub Environment approvals. DEV remains managed through ADF Studio Publish.

## Workflows

- `CI Workflow`: validates and exports ADF resources for a pull request.
- `ADF CD Pipeline`: promotes the exact CI artifact through SIT, UAT, and PROD, then enables PR auto-merge.
- `ADF Manual Deployment`: manually deploys the selected SIT, UAT, PRD, or DR configuration.

## Required GitHub Configuration

Create the following repository secret:

| Secret | Purpose |
|---|---|
| `AZURE_TENANT_ID` | Microsoft Entra tenant used by Azure OIDC login |

Create the following repository variables:

| Environment | Variables |
|---|---|
| DEV | `AZURE_DEV_SUBSCRIPTION_ID`, `AZURE_DEV_RESOURCE_GROUP`, `AZURE_DEV_DATA_FACTORY` |
| SIT | `AZURE_SIT_SUBSCRIPTION_ID`, `AZURE_SIT_RESOURCE_GROUP`, `AZURE_SIT_DATA_FACTORY`, `AZURE_SIT_CLIENT_ID` |
| UAT | `AZURE_UAT_SUBSCRIPTION_ID`, `AZURE_UAT_RESOURCE_GROUP`, `AZURE_UAT_DATA_FACTORY`, `AZURE_UAT_CLIENT_ID` |
| PROD | `AZURE_PROD_SUBSCRIPTION_ID`, `AZURE_PROD_RESOURCE_GROUP`, `AZURE_PROD_DATA_FACTORY`, `AZURE_PROD_CLIENT_ID` |

`GITHUB_TOKEN` is provided automatically by GitHub Actions and must not be created as a secret.

Create GitHub Environments named `sit`, `uat`, `prd`, and `dr`. Configure required reviewers for deployment approvals. OIDC federated credentials must use these exact environment names. DR currently reuses SIT Azure variables and client ID, but the SIT application registration still needs an additional federated credential for the `dr` GitHub Environment subject.

## Environment Configuration

Every target requires both files:

```text
adf/deploy/overrides/<environment>.overrides.json
adf/deploy/overrides/<environment>.template.overrides.json
```

Use environment keys `sit`, `uat`, `prd`, and `dr`. The first file supplies ARM parameter values such as `factoryName`. The second configures optional artifact mappings, property overrides, and forbidden DEV values. See [adf/deploy/overrides/README.md](adf/deploy/overrides/README.md).

Integration runtimes and managed private endpoints are not deployed by CI/CD. Provision them through the separate ADF environment setup before deployment. CI/CD can map linked-service references to a differently named pre-created IR.

For complete POC configuration and OIDC steps, see [SETUP.md](SETUP.md). The operating and approval model is documented in [CICD_STRATEGY.md](CICD_STRATEGY.md).
