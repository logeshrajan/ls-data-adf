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
adf/deploy/overrides/prod.overrides.json
adf/deploy/overrides/dr.overrides.json

adf/deploy/overrides/sit.template.overrides.json   (optional — only if IR names differ per env)
adf/deploy/overrides/uat.template.overrides.json
adf/deploy/overrides/prod.template.overrides.json
adf/deploy/overrides/dr.template.overrides.json
```

Each `<env>.overrides.json` patches the ARM parameters for that environment.
Minimum content (replace with actual factory name per env):
```json
{
  "factoryName": "mbb-adf-data-sit-myw-01"
}
```

### 1c. Deployment scripts

```
adf/deploy/scripts/validate_arm_json.py
adf/deploy/scripts/build_az_parameters_file.py
adf/deploy/scripts/apply_az_parameter_overrides.py
adf/deploy/scripts/apply_az_template_overrides.py
```

These scripts are referenced in the pipeline. They must exist before the pipeline can deploy.

---

## 2. Azure — App Registration + OIDC per Environment

The pipeline uses OIDC (no stored secrets). You need one App Registration per environment.

### For each environment (dev, sit, uat, prod):

**Step 1 — Create App Registration**
1. Azure Portal → Microsoft Entra ID → App registrations → New registration
2. Name: `github-adf-<env>` (e.g., `github-adf-sit`)
3. Note down: **Application (client) ID** and **Directory (tenant) ID**

**Step 2 — Add Federated Credential**
1. Open the App Registration → Certificates & secrets → Federated credentials → Add credential
2. Scenario: `GitHub Actions deploying Azure resources`
3. Fill in:
   - Organisation: `logeshrajan`
   - Repository: `ls-data-adf`
   - Entity type: `Environment`
   - GitHub environment name: `sit` (or `uat`, `prod`, `dr`)
4. Save

**Step 3 — Grant permissions on the ADF Resource Group**
1. Azure Portal → Resource Groups → `mbb-rg-dataingestion-<env>-myw-01`
2. Access control (IAM) → Add role assignment
3. Role: `Contributor`
4. Members: select the App Registration created in Step 1

> **POC shortcut**: If you have a single ADF factory and want to test quickly, use the same App Registration and the same subscription/resource group values for all environments.

---

## 3. GitHub — Secrets and Variables

### Secret (one for the entire repo)

Go to: **Settings → Secrets and variables → Actions → Secrets → New repository secret**

| Secret name | Value |
|---|---|
| `AZURE_TENANT_ID` | Your Azure Directory (tenant) ID |

### Variables (one set per environment)

Go to: **Settings → Secrets and variables → Actions → Variables → New repository variable**

| Variable name | Value |
|---|---|
| `AZURE_SIT_SUBSCRIPTION_ID` | Azure subscription ID for SIT |
| `AZURE_UAT_SUBSCRIPTION_ID` | Azure subscription ID for UAT |
| `AZURE_PROD_SUBSCRIPTION_ID` | Azure subscription ID for PROD |
| `AZURE_DEV_SUBSCRIPTION_ID` | Azure subscription ID for DEV (used only for ARM export) |
| `AZURE_SIT_CLIENT_ID` | Application (client) ID of the SIT App Registration |
| `AZURE_UAT_CLIENT_ID` | Application (client) ID of the UAT App Registration |
| `AZURE_PROD_CLIENT_ID` | Application (client) ID of the PROD App Registration |
| `AZURE_DEV_CLIENT_ID` | Application (client) ID of the DEV App Registration |

> **POC shortcut**: You can set all four subscription IDs to the same value and all four client IDs to the same App Registration if you only have one ADF instance.

---

## 4. GitHub — Environments

The pipeline uses GitHub Environments to enforce approval gates.

Go to: **Settings → Environments → New environment**

Create these four environments:

| Environment | Required reviewers | Notes |
|---|---|---|
| `sit` | SIT lead / tech lead | Add at least one reviewer |
| `uat` | QA lead / business analyst | Add at least one reviewer |
| `prod` | Release manager | Add at least one reviewer |
| `dr` | (optional) | No approval needed for DR testing |

For each environment: add the required reviewer(s) under **Required reviewers**.

---

## 5. GitHub — Branch Protection on `main`

Go to: **Settings → Branches → Add branch protection rule**

Branch name pattern: `main`

Enable:
- [x] Require a pull request before merging
- [x] Require approvals — set to **1**
- [x] Dismiss stale pull request approvals when new commits are pushed
- [x] Require branches to be up to date before merging
- [x] Do not allow bypassing the above settings

---

## 6. ADF Studio — Connect to This Repository

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

## 7. Run Your First Test

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

## 8. POC Checklist

- [ ] `adf/adf_resources/package.json` created
- [ ] Override files created for each env under `adf/deploy/overrides/`
- [ ] Deploy scripts created under `adf/deploy/scripts/`
- [ ] App Registration + federated credential created (at least for SIT)
- [ ] `AZURE_TENANT_ID` secret added to GitHub
- [ ] Subscription ID and Client ID variables added to GitHub
- [ ] GitHub environments created (`sit`, `uat`, `prod`)
- [ ] Reviewer added to at least the `sit` environment
- [ ] ADF Studio connected to this repo with `main` as collaboration branch
- [ ] First PR raised and pipeline run started
