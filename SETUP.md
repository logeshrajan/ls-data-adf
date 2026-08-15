# Pipeline Setup Guide

Follow these steps in order to get the CI/CD pipeline working end to end.

---

## 1. Repository Structure — What Must Exist

The pipeline expects the following files/folders. Create them if missing.

### 1a. ADF npm package

```
adf/adf_resources/package.json
```

Content:
```json
{
  "scripts": {
    "build": "node node_modules/@microsoft/azure-data-factory-utilities/lib/index"
  },
  "dependencies": {
    "@microsoft/azure-data-factory-utilities": "^1.0.0"
  }
}
```

### 1b. Environment override files

```
adf/deploy/overrides/sit.overrides.json
adf/deploy/overrides/uat.overrides.json
adf/deploy/overrides/prd.overrides.json
adf/deploy/overrides/dr.overrides.json

adf/deploy/overrides/sit.template.overrides.json
adf/deploy/overrides/uat.template.overrides.json
adf/deploy/overrides/prd.template.overrides.json
adf/deploy/overrides/dr.template.overrides.json
```

Each `<env>.overrides.json` patches the ARM parameters for that environment.
Minimum content (replace with actual factory name per env):
```json
{
  "factoryName": "ls-sit-adf"
}
```

Each `<env>.template.overrides.json` is required. It configures optional artifact name mappings, targeted property overrides, and forbidden DEV values. Use an empty configuration when no transformation is needed:

```json
{
  "artifactNameMappings": {},
  "propertyOverrides": [],
  "forbiddenValues": []
}
```

See `adf/deploy/overrides/README.md` for examples, including mapping a linked-service reference to a differently named pre-created integration runtime.

### 1c. Deployment scripts

```
adf/deploy/scripts/validate_arm_json.py
adf/deploy/scripts/build_az_parameters_file.py
adf/deploy/scripts/apply_az_parameter_overrides.py
adf/deploy/scripts/transform_adf_template.py
```

These scripts are referenced in the pipeline. They must exist before the pipeline can deploy.

---

## 2. Azure — App Registration + OIDC per Environment

The pipeline uses OIDC (no stored client secrets). You need **three** App Registrations — one each for SIT, UAT, and PROD. DR currently reuses the SIT App Registration.

> DEV does **not** need an SPN. DEV is deployed via ADF Studio Publish and this pipeline never logs in to Azure for DEV. CI uses the DEV subscription ID, resource group, and factory name only to construct the factory resource ID for ARM export; no DEV authentication is involved.

### For each of: sit, uat, prod

**Step 1 — Create App Registration**
1. Azure Portal → Microsoft Entra ID → App registrations → New registration
2. Name: `ls-data-spn-tier4-<env>-myw-01` (e.g., `ls-data-spn-tier4-sit-myw-01`)
3. Note down: **Application (client) ID** and **Directory (tenant) ID**

**Step 2 — Add Federated Credential**
1. Open the App Registration → Certificates & secrets → Federated credentials → Add credential
2. Fill in the form:
   - **Organization**: `logeshrajan`
   - **Organization ID**: run `curl https://api.github.com/users/logeshrajan` → copy the `id` value
   - **Repository**: `ls-data-adf`
   - **Repository ID**: run `curl https://api.github.com/repos/logeshrajan/ls-data-adf` → copy the `id` value
   - **Entity type**: `Environment`
    - **GitHub environment name**: `sit` (repeat this step for `uat` and `prd` with their respective App Registrations)
3. Save

Add a second federated credential to the SIT App Registration with GitHub environment name `dr`. Although DR reuses SIT Azure resources and `AZURE_SIT_CLIENT_ID`, its workflow job runs under the `dr` GitHub Environment and therefore has a different OIDC subject.

**Step 3 — Grant permissions on the ADF Resource Group**
1. Azure Portal → Resource Groups → `mbb-rg-dataingestion-<env>-myw-01`
2. Access control (IAM) → Add role assignment
3. Role: `Contributor`
4. Members: select the App Registration created in Step 1

> **POC shortcut**: One SPN can be reused, but it needs four federated credentials, one for each exact GitHub Environment subject: `sit`, `uat`, `prd`, and `dr`.

---

## 3. GitHub — Secrets and Variables

### Secret (one for the entire repo)

Go to: **Settings → Secrets and variables → Actions → Secrets → New repository secret**

| Secret name | Value |
|---|---|
| `AZURE_TENANT_ID` | Your Azure Directory (tenant) ID |

`GITHUB_TOKEN` is automatically created for each workflow run. Do not add it manually to repository secrets.

### Variables

Go to: **Settings → Secrets and variables → Actions → Variables → New repository variable**

| Variable name | Value | Notes |
|---|---|---|
| `AZURE_DEV_SUBSCRIPTION_ID` | Azure subscription ID for DEV | Used only to construct the factory resource ID for ARM export. No SPN or login needed. |
| `AZURE_DEV_RESOURCE_GROUP` | Resource group name for DEV ADF | e.g. `rg-adf-cicd` |
| `AZURE_DEV_DATA_FACTORY` | ADF factory name for DEV | e.g. `ls-dev-adf` |
| `AZURE_SIT_SUBSCRIPTION_ID` | Azure subscription ID for SIT | |
| `AZURE_SIT_RESOURCE_GROUP` | Resource group name for SIT ADF | |
| `AZURE_SIT_DATA_FACTORY` | ADF factory name for SIT | |
| `AZURE_UAT_SUBSCRIPTION_ID` | Azure subscription ID for UAT | |
| `AZURE_UAT_RESOURCE_GROUP` | Resource group name for UAT ADF | |
| `AZURE_UAT_DATA_FACTORY` | ADF factory name for UAT | |
| `AZURE_PROD_SUBSCRIPTION_ID` | Azure subscription ID for PROD | |
| `AZURE_PROD_RESOURCE_GROUP` | Resource group name for PROD ADF | |
| `AZURE_PROD_DATA_FACTORY` | ADF factory name for PROD | |
| `AZURE_SIT_CLIENT_ID` | Application (client) ID of `ls-data-spn-tier4-sit-myw-01` | |
| `AZURE_UAT_CLIENT_ID` | Application (client) ID of `ls-data-spn-tier4-uat-myw-01` | |
| `AZURE_PROD_CLIENT_ID` | Application (client) ID of `ls-data-spn-tier4-prd-myw-01` | |

Store these as repository variables so the automatic and manual workflows can resolve all target mappings. For a POC, the values may point to the same subscription or resource group, but the target factory names must still match the intended deployment targets.

---

## 4. GitHub — Environments

The pipeline uses GitHub Environments to enforce approval gates.

Go to: **Settings → Environments → New environment**

Create these four environments:

| Environment | Required reviewers | Notes |
|---|---|---|
| `sit` | SIT lead / tech lead | Add at least one reviewer |
| `uat` | QA lead / business analyst | Add at least one reviewer |
| `prd` | Release manager | Add at least one reviewer |
| `dr` | (optional) | No approval needed for DR testing |

For each environment: add the required reviewer(s) under **Required reviewers**.

The environment names must remain exactly `sit`, `uat`, `prd`, and `dr` because they are used in workflow jobs, environment configuration filenames, and OIDC federated credential subjects.

---

## 5. ADF Environment Prerequisites

Before the first CI/CD deployment, provision environment-owned resources outside this pipeline:

- Integration runtimes required by linked services.
- Managed private endpoints and their target-side approvals.
- Key Vaults and required secrets.
- Data Factory managed identity or user-assigned identity permissions.
- RBAC and network access required by linked services.

CI/CD removes integration runtime and managed-private-endpoint definitions from its ARM payload. Keep IR names stable across environments where possible. If an IR name differs, add an `integrationRuntime` mapping in the target `<env>.template.overrides.json` file so linked-service references resolve to the pre-created IR.

---

## 6. GitHub — Branch Protection on `main`

Go to: **Settings → Branches → Add branch protection rule**

Branch name pattern: `main`

Enable:
- [x] Require a pull request before merging
- [x] Require approvals — set to **1**
- [x] Dismiss stale pull request approvals when new commits are pushed
- [ ] Require status checks to pass before merging *(optional for POC — enable this and then check "Require branches to be up to date before merging" inside it for production use)*
- [x] Do not allow bypassing the above settings

---

## 7. ADF Studio — Connect to This Repository

1. Open your ADF instance in Azure Portal → Launch Studio
2. Go to **Manage** (toolbox icon) → **Git configuration**
3. Configure:
   - Repository type: `GitHub`
   - GitHub account: `logeshrajan`
   - Repository name: `ls-data-adf`
   - Collaboration branch: `main`
   - Publish branch: `adf_publish` (not used by this pipeline, but required by ADF)
   - Root folder: `/adf/adf_resources`
4. Save

---

## 8. Run Your First Test

Once all of the above is done:

```
1. In ADF Studio, create a simple pipeline (e.g., a Wait activity)
2. Save it — this commits to your current branch (or main)
3. Create a feature branch:
     git checkout -b feature/test-pipeline
4. Push the branch and open a PR against main on GitHub
5. The pipeline triggers:
     → build job: exports ARM template
     → deploy_sit job: waits for SIT approval
6. Go to GitHub Actions → the PR run → approve the SIT gate
7. SIT deploys
8. Approve UAT → PROD
9. After PROD: branch auto-merges to main
```

---

## 9. POC Checklist

- [ ] `adf/adf_resources/package.json` created
- [ ] Override files created for each env under `adf/deploy/overrides/`
- [ ] Deploy scripts created under `adf/deploy/scripts/`
- [ ] App Registrations created: `ls-data-spn-tier4-sit-myw-01`, `ls-data-spn-tier4-uat-myw-01`, `ls-data-spn-tier4-prod-myw-01`
- [ ] OIDC federated credentials configured for `sit`, `uat`, `prd`, and `dr`
- [ ] `AZURE_TENANT_ID` secret added to GitHub
- [ ] All DEV/SIT/UAT/PROD subscription, resource group, factory, and client ID variables added to GitHub
- [ ] GitHub environments created (`sit`, `uat`, `prd`, `dr`)
- [ ] Reviewer added to at least the `sit` environment
- [ ] Integration runtimes and managed private endpoints created outside CI/CD
- [ ] Managed private endpoints approved and identity/RBAC access verified
- [ ] ADF Studio connected to this repo with `main` as collaboration branch
- [ ] First PR raised and pipeline run started
