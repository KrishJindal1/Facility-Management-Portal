# HomeDesk Facility Management Portal — Production CI/CD & Deployment Guide (Render)

This document describes the complete Continuous Integration and Continuous Deployment (CI/CD) architecture connecting **GitHub**, **GitHub Actions**, and **Render Cloud Platform**.

---

## 1. End-to-End CI/CD Architecture Flow

```
                      +---------------------------------------+
                      |         Developer Workstation         |
                      |  1. Feature branch (git commit/push)  |
                      |  2. Open Pull Request to 'main'       |
                      +---------------------------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |            GitHub Actions CI          |
                      |  - Matrix: Python 3.11                |
                      |  - Service: PostgreSQL 15 Container   |
                      |  - Zero-secret mock AI testing        |
                      |  - 44 Unit & Integration Tests        |
                      +---------------------------------------+
                                          |
                      +-------------------+-------------------+
                      |                                       |
           [CI Fails: Exit 1]                      [CI Passes: Exit 0]
                      |                                       |
                      v                                       v
         PR Blocked / Red X in UI                 PR Approved & Merged
         No Deployment to Render                              |
                                                              v
                                          +---------------------------------------+
                                          |         GitHub Actions CD Job         |
                                          |  - Triggered ONLY on push to 'main'   |
                                          |  - Authenticates via Deploy Hook URL  |
                                          |  - Fires Render Deploy Webhook        |
                                          |  - Polls /_stcore/health endpoint     |
                                          +---------------------------------------+
                                                              |
                                                              v
                                          +---------------------------------------+
                                          |         Render Cloud Platform         |
                                          |  - Auto-Deploy: false (gated by CI)   |
                                          |  - Build: pip install requirements    |
                                          |  - Start: streamlit run app.py        |
                                          |  - Database: Render PostgreSQL        |
                                          |  - Production AI: OpenAI / Gemini     |
                                          +---------------------------------------+
```

---

## 2. CI/CD Workflow Breakdown

### CI Workflow (`test` Job)
The CI pipeline is defined in [`.github/workflows/ci.yml`](.github/workflows/ci.yml) and executes on:
- **Pull Requests targeting `main`**
- **Pushes to `main`**

**Execution Steps**:
1. **Runner**: Spin up clean `ubuntu-latest` virtual machine.
2. **Service Container**: Spin up isolated `postgres:15-alpine` container with automatic `pg_isready` healthcheck on port `5432`.
3. **Environment Isolation**: Set `AI_PROVIDER: mock` and ephemeral PostgreSQL test container credentials (`postgrespassword`). No production secrets required.
4. **Python Setup**: Provision Python `3.11` as specified in `.python-version` with automated pip caching.
5. **Dependency Installation**: Upgrade pip and install all locked packages from `requirements.txt`.
6. **Schema Initialization**: Execute `python -m database.init_db` against the PostgreSQL service container to generate schema tables and seed tenant test fixtures.
7. **Test Discovery & Execution**: Execute `python -m unittest discover -s tests -p "test_*.py" -v` across all 44 unit and integration tests.

### CD Workflow (`deploy` Job)
The deployment job runs **strictly** under the following conditions:
- Event is a `push` (or merged PR) directly onto `main`.
- The upstream `test` job completed with exit code `0` (`needs: test`).

**Execution Steps**:
1. **Render Deployment Trigger**:
   - Reads `RENDER_DEPLOY_HOOK_URL` from GitHub Repository Secrets.
   - Dispatches an authenticated `POST` request to Render's Deploy Hook endpoint.
   - Render pulls the validated commit SHA and starts a zero-downtime deployment.
2. **Post-Deploy Health Verification**:
   - Reads `RENDER_SERVICE_URL` from GitHub Repository Secrets (e.g. `https://homedesk-facility-portal.onrender.com`).
   - Polls the native Streamlit health endpoint (`/_stcore/health`) every 10 seconds for up to 5 minutes.
   - Confirms HTTP 200 status before marking the deployment workflow as green.

---

## 3. Configuration & Secrets Management

Secrets and configuration are strictly segregated between **GitHub Actions** (deployment orchestration) and **Render** (runtime execution).

### A. GitHub Repository Secrets
Navigate to: **GitHub Repo** &rarr; **Settings** &rarr; **Secrets and variables** &rarr; **Actions** &rarr; **New repository secret**:

| Secret Name | Required? | Purpose | Example Value |
|---|---|---|---|
| `RENDER_DEPLOY_HOOK_URL` | **Yes** (for CD) | Webhook to trigger Render deployment after CI succeeds | `https://api.render.com/deploy/srv-abc123xyz?key=secrettoken` |
| `RENDER_SERVICE_URL` | Optional | URL of the live Render app used for post-deployment health verification | `https://homedesk-facility-portal.onrender.com` |

> **Note:** The CI test suite does **not** require any production secrets. It runs completely hermetic with `AI_PROVIDER=mock` and an ephemeral containerized PostgreSQL instance.

### B. Render Production Environment Variables
Navigate to: **Render Dashboard** &rarr; **Web Service** &rarr; **Environment**:

| Variable Name | Required? | Purpose | Example Value |
|---|---|---|---|
| `PYTHON_VERSION` | Yes | Specifies Python runtime version | `3.11.9` |
| `APP_ENV` | Yes | Enables production mode | `production` |
| `DATABASE_URL` | Yes | Internal PostgreSQL connection string | `postgres://homedesk_admin:***@dpg-***-a/facility_management` |
| `AI_PROVIDER` | Yes | Active AI engine | `openai` (or `gemini`) |
| `AI_API_KEY` | Yes | Production API key for cloud AI | `sk-proj-************************` |
| `AI_MODEL` | Yes | LLM model identifier | `gpt-4o-mini` |
| `AI_API_BASE_URL` | Optional | Custom endpoint (e.g. for Groq) | `https://api.openai.com/v1` |

> **Security Guarantee:** Render secrets and keys are never stored in git or exposed in CI logs.

---

## 4. How a Developer Safely Releases a Change

Follow this workflow to release updates safely to production:

### Step 1: Work in a Feature Branch
```bash
git checkout -b feature/improved-lead-routing
# Make your code edits...
```

### Step 2: Validate Locally Before Pushing
Run the automated test suite locally:
```bash
python -m unittest discover tests -v
```
Run the system health check:
```bash
python healthcheck.py
```

### Step 3: Push and Open a Pull Request
```bash
git push -u origin feature/improved-lead-routing
```
Open a Pull Request on GitHub targeting the `main` branch.

### Step 4: GitHub Actions Validates the PR
- GitHub Actions automatically runs the `test` job.
- The `deploy` job is **automatically skipped** on pull requests.
- Branch protection rules prevent merging until all CI checks pass.

### Step 5: Merge Pull Request
Once approved and CI passes, merge the PR into `main`.

### Step 6: Automated Production Deployment
1. GitHub Actions detects the push to `main` and runs the `test` job.
2. Upon test success, GitHub Actions executes the `deploy` job.
3. Render receives the deploy webhook, builds the application, and transitions traffic with zero downtime.
4. GitHub Actions verifies that `https://<service-url>/_stcore/health` responds with HTTP 200 OK.

---

## 5. Failure Handling & Resilience

### What Happens When CI Fails?
- If any unit test, database query, or lint check fails during the `test` job:
  1. The GitHub Actions job immediately terminates with an error code.
  2. The Pull Request displays a prominent **Red X**, blocking merging.
  3. The downstream `deploy` job **does not run**.
  4. Render is **never notified** of the faulty commit.
  5. The live production service continues running the previous healthy deployment without disruption.

### What Happens When Render Deployment Fails?
- If the build fails on Render (e.g., dependency installation failure or compilation error):
  1. Render cancels the rollout.
  2. Render keeps the previous successful container version running (zero downtime).
  3. The GitHub Actions post-deploy health check detects that the new deployment did not become healthy and flags the pipeline with an error.
  4. Detailed diagnostics can be inspected directly in the Render Web Service deployment log or via `python healthcheck.py`.

---

## 6. Render Service Setup Reference

### Web Service Configuration
- **Repository**: `https://github.com/KrishJindal1/Facility-Management-Portal`
- **Branch**: `main`
- **Runtime**: `Python`
- **Auto-Deploy**: `No` (*Gated via GitHub Actions Deploy Hook*)
- **Build Command**:
  ```bash
  pip install --upgrade pip && pip install -r requirements.txt
  ```
- **Start Command**:
  ```bash
  streamlit run app.py --server.address=0.0.0.0 --server.port=$PORT
  ```
- **Health Check Path**:
  ```
  /_stcore/health
  ```
