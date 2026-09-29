# HomeDesk — Cloud Facility Management Portal

HomeDesk is a multi-tenant cloud facility management portal built with **Streamlit**, **PostgreSQL**, and **Cloud AI (OpenAI / Gemini / Groq)**. It provides end-to-end workflows for capturing, managing, and servicing facility requests (Cook, Driver, Security Guard) with strict multi-tenant isolation, user authentication, and an intelligent AI assistant.

---

## Key Features

- **Multi-Tenant Architecture**: Complete tenant partitioning by organization (`homedesk`, `acme`, etc.). Each organization maintains isolated leads, users, sequential lead IDs, and reporting data.
- **Secure Authentication**: Salted bcrypt password hashing, session context locking, and multi-user organization management.
- **Service Request Forms**: Validated requirement intake for Cook, Driver, and Security Guard services with automated lead ID generation (`Cook-1001`, `Driver-1001`, `Security-1001`).
- **Lead Lookup & Tracking**: Real-time status lookup by contact number, scoped strictly to the authenticated tenant.
- **AI Assistant Widget**: Cloud-native conversational AI powered by OpenAI, Groq, or Google Gemini with local Ollama fallback for offline development.
- **Production Data Layer**: PostgreSQL source of truth with connection pooling and dialect normalization, plus Excel export capabilities.
- **Continuous Integration**: GitHub Actions CI pipeline running 44 automated unit and integration tests with a PostgreSQL service container.

---

## Local Development Setup

### 1. Prerequisites
- Python 3.11+
- Virtual environment tool (`venv`)

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/KrishJindal1/Facility-Management-Portal.git
cd Facility-Management-Portal

# Create and activate virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy the example environment template:
```bash
cp .env.example .env
```
Edit `.env` to configure your database and cloud AI credentials:
```ini
APP_ENV=development
DATABASE_URL=sqlite:///data/facility_management.db  # Or your local postgresql:// connection
AI_PROVIDER=openai
AI_API_KEY=your-api-key-here
AI_MODEL=gpt-4o-mini
```

### 4. Running the Application Locally
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## Running Automated Tests

Run the full test suite locally:
```bash
python -m unittest discover tests -v
```

Run the production readiness health check:
```bash
python healthcheck.py
```

---

## CI/CD Pipeline & Production Deployment (Render)

The application features a fully automated Continuous Integration and Continuous Deployment (CI/CD) workflow:

1. **Pull Request Validation**: Every PR is validated by GitHub Actions against Python 3.11 and an automated PostgreSQL container (44 unit & integration tests).
2. **Main Branch Gating**: Deployments to Render occur **only** after CI succeeds on `main`.
3. **Automated Render Rollout**: GitHub Actions triggers the Render Deploy Hook securely via secrets.
4. **Post-Deploy Verification**: Automated health checks ping `/_stcore/health` to confirm zero-downtime availability.

### Configuration Reference
- **GitHub Workflow**: [`.github/workflows/ci.yml`](.github/workflows/ci.yml)
- **Render Blueprint**: [`render.yaml`](render.yaml)
- **Comprehensive Guide**: See [`DEPLOYMENT.md`](DEPLOYMENT.md) for full instructions, secrets setup, and release procedures.
