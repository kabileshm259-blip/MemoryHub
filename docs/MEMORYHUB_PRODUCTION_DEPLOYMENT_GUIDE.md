# MemoryHub — Production Hosting & Public Deployment Specification

**Project:** MemoryHub — AI-Based Handoff Framework for Seamless Organizational Operational Continuity  
**Workspace:** `C:\Projects\MemoryHub`  
**Target Topology:**
- **Frontend Tier:** Vercel (Next.js 16 App Router, React 19, Tailwind CSS)
- **Backend API Tier:** Render (FastAPI, Python 3.11, Uvicorn)
- **Primary Relational Store:** Managed PostgreSQL (Render PostgreSQL, Supabase, Neon, or AWS RDS)
- **Vector Retrieval Engine:** Rehydration-Resilient In-Memory Index backed by PostgreSQL (Optional: Cloud-hosted ChromaDB)
- **AI Synthesis Engine:** Google Gemini 2.5 Flash (Backend-only, bounded latency, heuristic circuit-breaker fallback)

---

## 1. Architectural Topology & Network Flow

```
+---------------------------------------------------------------------------------------+
|                                    CLIENT BROWSER                                     |
+---------------------------------------------------------------------------------------+
        |                                                                |
        | 1. Web Assets & Pages (HTTPS)                                  | 2. API Requests (HTTPS / JSON / JWT)
        v                                                                v
+-----------------------------------+            +--------------------------------------+
|          VERCEL HOSTING           |            |            RENDER HOSTING            |
|  - Root: `frontend`               |            |  - Root: `backend`                   |
|  - Framework: Next.js (App Router)|            |  - Web Service: `uvicorn` on 0.0.0.0 |
|  - NEXT_PUBLIC_API_BASE_URL:      |            |  - Health Check: `/health`           |
|    https://<render-api>.com       |            |  - Strict CORS validation            |
+-----------------------------------+            +-------------------+------------------+
                                                                     |
                       +---------------------------------------------+------------------------------------+
                       |                                             |                                    |
                       v                                             v                                    v
+-----------------------------------------------+   +---------------------------------+  +-------------------------------+
|             MANAGED POSTGRESQL                |   |    INTERNAL VECTOR ENGINE       |  |     GOOGLE GEMINI 2.5 FLASH   |
|  - Render Postgres / Supabase / Neon          |   |  - 384-dimensional embeddings   |  |  - Official `google-genai`    |
|  - Relational tables: projects, handoffs,     |   |  - Auto-rehydrates from DB      |  |  - Strict system instructions |
|    source_records, users, notifications       |   |  - Optional: Cloud ChromaDB     |  |  - Citations validated        |
|  - Connection: `DATABASE_URL`                 |   |    via `CHROMA_URL`             |  |  - API Key: Backend ONLY      |
+-----------------------------------------------+   +---------------------------------+  +-------------------------------+
```

---

## 2. Deployment Requirements & Code Audit Findings

| Requirement Area | Code Audit Finding | Production Strategy |
| :--- | :--- | :--- |
| **FastAPI Import Path & Startup** | `backend/app/main.py` defines `app = FastAPI(...)`. | Run from `backend` working directory: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. |
| **Python Version & Dependencies** | Python 3.11 with dependencies pinned in `backend/requirements.txt` (FastAPI 0.162.0, SQLAlchemy 2.0.44, psycopg 3.2.13, google-genai 2.33.0). | Render environment variable `PYTHON_VERSION=3.11.0`. Install with `pip install -r requirements.txt`. |
| **Frontend Build & Start** | Next.js 16.4.3 Turbopack configured in `frontend/package.json` (`next build`, `next start`). | Vercel preset: Next.js, Root Directory: `frontend`, Build Command: `next build`. |
| **Frontend API Base URL** | `frontend/src/lib/api.ts` initializes `API_BASE_URL` from `process.env.NEXT_PUBLIC_API_BASE_URL` with `.replace(/\/+$/, "")` to prevent double-slash errors. | Set Vercel environment variable `NEXT_PUBLIC_API_BASE_URL=https://<your-render-service>.onrender.com`. |
| **CORS Middleware** | `backend/app/main.py` dynamically parses `CORS_ORIGINS` from environment while preserving local development origins. Supports Vercel preview regex via `ALLOW_VERCEL_PREVIEWS=true`. | Set Render environment variable `CORS_ORIGINS=https://<your-vercel-app>.vercel.app`. |
| **Database Connection & Normalization** | `backend/app/database.py` accepts `DATABASE_URL` and normalizes `postgres://` or `postgresql://` to `postgresql+psycopg://` for SQLAlchemy 2.0 and psycopg3. | Render or external PostgreSQL connection string configured in `DATABASE_URL`. |
| **Alembic Migrations** | Current migration chain: `855f92dcd5c7` -> `01ba3083209e` -> `c4d87a912b3f (head)`. Compatible with PostgreSQL and SQLite. | Run before server boot: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`. |
| **Vector Store & Data Persistence** | `VectorService` utilizes `InMemoryVectorStore` with automatic `rehydrate_from_db(project_id)` that reconstructs embeddings directly from PostgreSQL `source_records`. | Single source of truth is PostgreSQL. Zero data loss across server restarts. ChromaDB can be connected via `CHROMA_URL` when cloud instance is provisioned. |
| **Gemini Key Isolation** | `GEMINI_API_KEY` is loaded only in `backend/app/config.py` and accessed solely by `backend/app/services/gemini_service.py`. | Zero leakage: No frontend code or browser bundle ever receives or invokes Gemini API keys. |
| **Health Check Endpoints** | `/health` (zero-dependency liveness) and `/health/readiness` (PostgreSQL + vector status). | Configure Render health check path to `/health`. |
| **Data Loss Prevention** | In production (`ENVIRONMENT=production` or `REQUIRE_POSTGRES=true`), `database.py` enforces a strict PostgreSQL connection and refuses silent fallback to ephemeral SQLite. | Guarantees that ephemeral container filesystem wipes on Render will never cause silent data loss. |

---

## 3. Configuration Specifications

### 3.1 Backend Configuration (Render)

#### Render Service Settings
- **Service Type:** Web Service
- **Runtime:** Python 3
- **Root Directory:** `backend`
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Health Check Path:** `/health`
- **Auto-Deploy:** Yes (on Git push to `main`)

#### Required Backend Environment Variables

| Variable Name | Required | Default / Example Value | Description |
| :--- | :---: | :--- | :--- |
| `ENVIRONMENT` | Yes | `production` | Enforces production mode and strict PostgreSQL persistence guard. |
| `DATABASE_URL` | Yes | `postgresql+psycopg://...` | Connection URI to managed PostgreSQL (provided by Render Postgres or external). |
| `JWT_SECRET` | Yes | *Minimum 32 random characters* | Secret key for signing and verifying user session JWT tokens. |
| `JWT_ALGORITHM` | No | `HS256` | Cryptographic algorithm for JWT encoding. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `60` | Token lifetime before re-authentication is required. |
| `CORS_ORIGINS` | Yes | `https://<your-app>.vercel.app` | Comma-separated list of allowed production frontend domains. |
| `ALLOW_VERCEL_PREVIEWS` | No | `true` | When true, permits CORS from Vercel preview deployments (`*.vercel.app`). |
| `AI_PROVIDER` | Yes | `gemini` | Configures the primary AI synthesis engine (`gemini` or `heuristic`). |
| `GEMINI_API_KEY` | Yes | *Google AI Studio API Key* | API key for Gemini 2.5 Flash inference. Kept strictly on backend. |
| `GEMINI_MODEL` | No | `gemini-2.5-flash` | Gemini model variant identifier. |
| `GEMINI_TIMEOUT_SECONDS` | No | `15.0` | Maximum network timeout for Gemini API calls before circuit-breaker fires. |
| `GEMINI_MAX_OUTPUT_TOKENS` | No | `1024` | Token generation ceiling for bounded latency. |
| `CHROMA_URL` | No | `http://127.0.0.1:8001` | Optional URL if external ChromaDB service is provisioned. |

---

### 3.2 Frontend Configuration (Vercel)

#### Vercel Project Settings
- **Framework Preset:** Next.js
- **Root Directory:** `frontend`
- **Build Command:** `next build` (or `npm run build`)
- **Output Directory:** `.next`
- **Install Command:** `npm install`
- **Node.js Version:** 20.x or 22.x

#### Required Frontend Environment Variables

| Variable Name | Required | Example Value | Description |
| :--- | :---: | :--- | :--- |
| `NEXT_PUBLIC_API_BASE_URL` | Yes | `https://memoryhub-api.onrender.com` | Base URL of the deployed FastAPI backend. Must NOT include a trailing slash. |

---

## 4. Database & Vector-Store Strategy

### 4.1 PostgreSQL Deployment
MemoryHub requires PostgreSQL 15+ with standard UUID and JSONB capabilities.

1. **Option A — Render Managed PostgreSQL (Recommended for simplicity):**
   - In Render Dashboard, click **New +** -> **PostgreSQL**.
   - Set Name to `memoryhub-postgres`, Database to `memoryhub`, User to `memoryhub_user`.
   - Copy the **Internal Connection String** (or External if connecting from outside Render).
   - In Render Web Service, attach `DATABASE_URL` directly from the PostgreSQL instance.
2. **Option B — External Managed PostgreSQL (Supabase / Neon / AWS RDS):**
   - Provision a PostgreSQL database on Supabase or Neon.
   - Copy the connection string. Ensure driver prefix is `postgresql://` or `postgresql+psycopg://`.
   - Set `DATABASE_URL` in Render environment variables.

### 4.2 Migration Execution
Alembic migrations are configured to run automatically before the FastAPI server starts:
```bash
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```
This guarantees:
- All tables (`projects`, `users`, `handoffs`, `source_records`, `handoff_comments`, `notifications`) are created or upgraded to `c4d87a912b3f (head)` before incoming requests are accepted.
- Existing data is preserved without table drops or schema truncation.

### 4.3 Vector Store Persistence
- **Primary Mechanism:** Vector embeddings are generated using MemoryHub's deterministic 384-dimensional `VectorEmbeddingEngine`.
- **Durability Guarantee:** When documents and Jira/Slack sources are ingested, raw text and metadata are committed to the persistent `source_records` table in PostgreSQL.
- **Cold-Start Resilience:** If the Render web service restarts or redeploys, `VectorService.rehydrate_from_db(project_id)` automatically rebuilds the vector index in memory upon the first query, guaranteeing 100% data continuity without losing indexed memory.
- **ChromaDB Cloud Transition:** If a dedicated ChromaDB instance is deployed (e.g., via Docker on Render or AWS), simply set `CHROMA_URL=https://<chroma-service-url>` to activate persistent two-way syncing.

---

## 5. Step-by-Step Operator Deployment Guide

### Phase 1: Database Provisioning (5 minutes)
1. Log in to [Render](https://dashboard.render.com).
2. Click **New +** -> **PostgreSQL**.
3. Configure:
   - **Name:** `memoryhub-postgres`
   - **Database:** `memoryhub`
   - **User:** `memoryhub_user`
   - **Region:** Same region as your web service (e.g., Oregon or Frankfurt)
   - **Plan:** Free or Starter
4. Click **Create Database**.
5. Once active, copy the **Internal Database URL**.

### Phase 2: Deploy Backend to Render (5 minutes)
1. In Render Dashboard, click **New +** -> **Web Service**.
2. Connect your Git repository (`https://github.com/kabileshm259-blip/MemoryHub.git`).
3. Configure service:
   - **Name:** `memoryhub-api`
   - **Region:** Same as database
   - **Branch:** `main`
   - **Root Directory:** `backend`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. In **Advanced** -> **Health Check Path**, enter: `/health`.
5. Under **Environment Variables**, add:
   - `ENVIRONMENT` = `production`
   - `DATABASE_URL` = *(Paste Internal Database URL from Phase 1)*
   - `JWT_SECRET` = *(Generate a 32+ character random string)*
   - `AI_PROVIDER` = `gemini`
   - `GEMINI_API_KEY` = *(Your Google AI Studio Gemini API Key)*
   - `GEMINI_MODEL` = `gemini-2.5-flash`
   - `CORS_ORIGINS` = `https://<your-vercel-domain>.vercel.app` *(Can update after Phase 3)*
   - `ALLOW_VERCEL_PREVIEWS` = `true`
6. Click **Create Web Service**.
7. Wait for deployment to complete. Verify at `https://memoryhub-api.onrender.com/health` &rarr; `{"status":"ok","service":"memoryhub-api"}`.

### Phase 3: Deploy Frontend to Vercel (5 minutes)
1. Log in to [Vercel](https://vercel.com).
2. Click **Add New...** -> **Project**.
3. Import your Git repository.
4. In Project Configuration:
   - **Framework Preset:** `Next.js`
   - **Root Directory:** Click **Edit** and select `frontend`.
5. Under **Environment Variables**, add:
   - **Key:** `NEXT_PUBLIC_API_BASE_URL`
   - **Value:** `https://memoryhub-api.onrender.com` *(Replace with your real Render URL, no trailing slash)*
6. Click **Deploy**.
7. Vercel will compile the Next.js application and assign a production URL (e.g., `https://memoryhub.vercel.app`).

### Phase 4: Finalize CORS Handshake (2 minutes)
1. Copy your Vercel production URL (e.g., `https://memoryhub.vercel.app`).
2. Go back to Render -> `memoryhub-api` -> **Environment**.
3. Update `CORS_ORIGINS` to include your Vercel URL:
   `https://memoryhub.vercel.app`
4. Render will automatically redeploy with the updated CORS configuration.

---

## 6. Public Verification Runbook

Once both services are deployed:
1. **Health Verification:**
   - Visit `https://<your-render-url>/health` &rarr; Expect HTTP 200 `{"status":"ok","service":"memoryhub-api"}`.
   - Visit `https://<your-render-url>/health/readiness` &rarr; Expect HTTP 200 `{"status":"ready","postgres":"connected","database_mode":"postgresql"}`.
2. **Frontend Loading:**
   - Visit `https://<your-vercel-url>/login`.
   - Verify that the login page loads cleanly without any "Unable to connect to MemoryHub backend" error banner.
3. **Authentication & Session:**
   - Register a new administrative account or sign in.
   - Confirm successful JWT receipt and redirect to `/dashboard`.
4. **AI Knowledge Chat (`/chat`):**
   - Ingest a sample source document or sync Jira tickets on `/sources`.
   - Navigate to `/chat`.
   - Ask an evidence-grounded question.
   - Verify:
     - Badge displays **Gemini 2.5 Flash**.
     - Synthesized response returns with citation card.
     - Asking an out-of-scope question triggers the **Insufficient Evidence** honest abstention banner.
5. **Operational Handoff Generation (`/handoffs`):**
   - Click **AI Handoff Generator**.
   - Observe multi-stage animated workflow completion with server-confirmed readiness score, task counts, and risk counts.

