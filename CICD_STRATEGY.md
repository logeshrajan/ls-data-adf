# CI/CD and Branching Strategy — ADF Data Platform

## Branch Model

```
feature/* , fix/*
      │
      ▼  (PR + code review)
          main  ──→  CI build/validate  ──→  SIT (approval)  ──→  UAT (approval)  ──→  PROD (approval)  ──→  auto-merge
```

> DEV is deployed by the developer directly via **ADF Studio Publish** — not by this pipeline.

One long-lived branch only:

| Branch | Purpose | Who merges to it |
|---|---|---|
| `main` | Always reflects exactly what is in PROD. | Pipeline auto-merges after PROD succeeds |

Feature and fix branches are short-lived. They are **never manually merged** — the pipeline merges them to `main` automatically after PROD approval.

---

## Pipeline: What Triggers What

### On PR opened or updated against `main`

```
CI build + validation  ──success──▶  SIT  ──approval──▶  UAT  ──approval──▶  PROD  ──approval──▶  auto-merge
                                ▲                   ▲                    ▲
                           SIT lead /          QA lead / BA        Release manager
                           tech lead
```

- **CI**: runs for every PR commit, exports and validates the ARM template, and publishes an immutable artifact. A newer commit cancels an older CI build for the same PR.
- **CD**: starts only after CI succeeds and downloads the artifact from that exact CI run.
- **DEV**: deployed by the developer via ADF Studio Publish before raising the PR. Not part of this pipeline.
- **SIT**: first pipeline stage. Pauses for SIT lead / tech lead approval. Approver also checks whether the branch needs a rebase before approving.
- **UAT**: pauses for QA lead / business analyst approval. At most one PR can be in UAT at a time.
- **PROD**: pauses for release manager approval. Pipeline auto-merges the branch to `main` after success.

---

## Approval Gates Summary

| Environment | Triggered by | Auto or Approval | Who approves |
|---|---|---|---|
| DEV | ADF Studio Publish (manual) | **Developer** | Developer |
| SIT | successful PR CI run | **Approval** | SIT lead / tech lead |
| UAT | after SIT passes | **Approval** | QA lead / business analyst |
| PROD | after UAT passes | **Approval** | Release manager |

### What "approval" means in practice
GitHub pauses the run and notifies the configured reviewers. The approver goes to the workflow run in GitHub Actions and clicks **Approve** or **Reject**.

- **Approve** → deployment proceeds immediately
- **Reject** → run fails cleanly. Developer pushes a fix to the same PR branch — the process restarts from CI.

### PR approval versus environment approval

These are separate controls:

- **PR approval** is a code review. It must come from another authorized reviewer; the PR author cannot approve their own PR.
- **Environment approval** authorizes deployment to SIT, UAT, or PROD. It does not satisfy the required PR code review.

CI starts immediately when the PR is opened or updated. The recommended order is:

```text
PR opened -> CI succeeds -> PR approved by another reviewer -> SIT approval -> UAT approval -> PROD approval -> auto-merge
```

After PROD succeeds, the pipeline enables GitHub auto-merge. GitHub completes the merge only after all branch protection requirements, including the required PR approval and status checks, are satisfied.

---

## Rebase Rule — Required Before UAT

**Who does it**: The developer (not the approver).  
**When**: The SIT approver checks whether the feature branch is behind `main` before approving. If it is behind, they hold and ask the developer to rebase first.

**What the developer runs:**
```bash
git fetch origin
git rebase origin/main
git push --force-with-lease origin feature/<branch-name>
```

This replays the developer's commits on top of the latest `main`, so the deployment snapshot includes all previous PROD deployments. CI re-triggers automatically after the push.

**Why this matters**: ADF ARM deployments are incremental — they do not delete other workstreams' resources. But if two PRs both modify a shared resource (e.g., a linked service), whichever deploys last wins. The rebase ensures the snapshot going to PROD is always the most up-to-date version of shared resources.

---

## Concurrency Rules

Multiple PRs in flight simultaneously all target the same ADF factories. Concurrency groups prevent conflicts:

| Environment | Behaviour |
|---|---|
| SIT | Queue — one at a time |
| UAT | Queue — never cancel a run that may be mid-deployment |
| PROD | Queue — never cancel a run that may be mid-deployment |

DEV has no concurrency rules — it is managed by ADF Studio Publish, outside the pipeline.

**Example**: PR-1 (AEA) is at UAT. PR-2 (CFS) finishes SIT and tries to enter UAT — it waits in the queue. PR-1 must complete UAT before PR-2 can proceed. Each PR needs its own separate approval.

---

## Snapshot Guarantee

CI locks the PR commit SHA and publishes its ARM artifact. The downstream CD run downloads that exact artifact, and every stage — SIT, UAT, PROD — deploys the **same snapshot**. Pushing a new commit starts a new CI run and, after CI succeeds, a new CD run from SIT. Each CD stage verifies that its SHA is still the latest PR commit before deployment.

Combined with the rebase rule, the snapshot that reaches PROD always includes everything already in `main` and is consistent across all stages.

---

## Developer Workflows

### 1. Normal feature / fix development

```
1. git checkout main && git pull
2. git checkout -b feature/aea-<ticket>   (or fix/<ticket>)
3. Develop and commit locally; use ADF Studio Publish to test in DEV
4. Open PR against main when DEV testing is complete
5. Code review → approved
6. CI builds and validates the ARM artifact
7. Successful CI automatically starts CD:
     SIT gate: SIT lead checks rebase, then approves
     UAT gate: QA approves after testing
     PROD gate: release manager approves
     → pipeline auto-merges branch to main
```

### 2. Bug found in SIT or UAT

```
1. git checkout main && git pull
2. git checkout -b fix/aea-<description>
3. Fix the bug; use ADF Studio Publish to verify in DEV
4. Open PR against main
5. Code review → approved
6. Pipeline triggers fresh:
     SIT approval (fast-tracked — it's a fix)
     UAT approval (fast-tracked)
     PROD approval (fast-tracked)
     → auto-merge to main
```

### 3. Critical production hotfix

Same flow as a normal fix — raise a PR against `main` and mark it as a hotfix so approvers fast-track it. No separate back-merge step is needed because there is only one long-lived branch.

---

## Branch Protection Rules

### `main`
- Require pull request before merging
- Require at least 1 approving review (code review)
- Dismiss stale reviews when new commits are pushed
- Require branches to be up to date before merging
- Block direct pushes — no force push
- Do not allow bypassing the above settings (applies to admins too)

Pipeline auto-merge after PROD is performed via a dedicated service account / GitHub App that has merge permissions.

---

## Where Each Workstream Lives

| Workstream | Status | How it moves to PROD |
|---|---|---|
| AEA | Production-ready | Raise PR to `main` — goes through full pipeline |
| CFS | In development | Raise PR to `main` — goes through full pipeline independently |
| ESPI | In development | Raise PR to `main` — goes through full pipeline independently |

Each workstream's PR is independent. CFS being in SIT does not block AEA from being in UAT simultaneously. They only queue at UAT/PROD where a single factory is the deployment target.

---

## ADF Studio Git Configuration

ADF Studio must be configured to use `main` as the collaboration branch. Developers create feature branches within ADF Studio, make changes, and use the **Publish** button to deploy to DEV for testing. Once satisfied, they raise a PR — the CI/CD pipeline takes over from SIT onwards.

**Setting**: ADF Studio → Manage → Git configuration → Collaboration branch → `main`

---

## Manual Re-deployment (workflow_dispatch)

For emergency or ad-hoc deployments without raising a PR. Go to GitHub → Actions → **ADF CD Pipeline** → **Run workflow**, select the environment, and click Run.

| Available environment | When to use |
|---|---|
| `sit` | Re-deploy to SIT without a code change (e.g., factory was manually modified) |
| `uat` | Re-deploy to UAT before QA sign-off |
| `prod` | Emergency re-deploy to PROD (approvals still enforced by environment rules) |
| `dr` | DR testing on demand |

`dev` is **not available** here — DEV is managed by ADF Studio Publish.

---

## Key Rules — Quick Reference

| Rule | Why |
|---|---|
| Always branch from `main` | Your work starts from the latest PROD state |
| Never push directly to `main` | Branch protection enforces this |
| Rebase before UAT | Prevents a stale snapshot overwriting a shared resource in PROD |
| One PR in UAT/PROD at a time | Prevents concurrent writes to the same factory |
| Pipeline auto-merges after PROD | `main` always = PROD, no manual merge needed |
| Push a fix to the same PR to re-trigger | No dummy commits — same PR, new pipeline run |

---

## Simple Version — The Three Rules

> This is all you need to remember day to day.

**Rule 1 — Developer (rebase):**  
Before your PR enters UAT, make sure your branch includes everything already in `main`:
```bash
git rebase origin/main && git push --force-with-lease
```

**Rule 2 — Pipeline (queue):**  
Only one PR can be in UAT or PROD at a time. If another PR is there, yours waits automatically — no action needed.

**Rule 3 — Auto-merge:**  
After PROD succeeds, the pipeline merges your branch to `main` for you. You do not merge it manually.

That is the entire model. Every other section in this document is detail around these three rules.
