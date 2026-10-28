# MemoryHub

> **Centralized Knowledge and Handoff Platform for Engineering Teams**

MemoryHub is an engineering intelligence system designed to preserve project context, team ownership, and architectural knowledge across development lifecycles.

---

## Architecture

- **Backend**: FastAPI (Python 3.11), SQLAlchemy 2.0 ORM, Alembic schema migrations, Pydantic v2 schemas.
- **Frontend**: Next.js 16 (App Router, Turbopack), React 19, TypeScript 5, Tailwind CSS v4.
- **Data Layer**: PostgreSQL 17 (relational metadata, users, memberships, projects) and ChromaDB (vector embeddings).

---

## Quick Start

### 1. Start Infrastructure Services

Make sure Docker is running, then start the PostgreSQL and ChromaDB containers:
```powershell
docker compose -f infrastructure/compose.postgres.yaml up -d
docker compose -f infrastructure/compose.chroma.yaml up -d
```

Verify container status:
```powershell
docker ps
```

### 2. Configure Environment

Copy `.env.example` to `.env` in the repository root:
```powershell
cp .env.example .env
```

### 3. Start the Backend API

```powershell
cd backend
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
- API Base URL: `http://127.0.0.1:8000`
- Interactive OpenAPI Docs: `http://127.0.0.1:8000/docs`
- Health Readiness Probe: `http://127.0.0.1:8000/health/readiness`

### 4. Start the Frontend Application

In a separate terminal:
```powershell
cd frontend
cp .env.example .env.local
npm install
npm run dev
```
- Frontend Web App: `http://localhost:3000`

---

## Implemented Modules & Roadmaps

| Module | Status | Details |
| :--- | :---: | :--- |
| **Authentication & RBAC** | ✅ Complete | JWT authentication, bcrypt password hashing, `GET /api/auth/me`, role-based permissions (`Owner`, `Editor`, `Viewer`). |
| **Project Workspace** | ✅ Complete | Full CRUD operations, owner-only project settings, membership rosters, email-based invitations. |
| **Web UI Dashboard** | ✅ Complete | App shell, navigation sidebar, project metrics, dynamic forms, validation toasts, route protection. |
| **Handoff Pipeline** | ⏳ Phase 3 Step 2 | Automated developer handover generation and context snapshotting. |
| **Knowledge Sources** | ⏳ Phase 3 Step 3 | Ingestion pipelines for Git repos, documentation, and tickets. |
| **Third-Party Integrations** | ⏳ Phase 3 Step 4 | Jira Cloud, GitHub, and Slack synchronization webhooks. |

---

## Running Automated Tests

### Backend Unit & Integration Tests (Pytest)
```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\ -v
```

### Frontend Linting & Build Verification
```powershell
cd frontend
npm run lint
npm run build
```
