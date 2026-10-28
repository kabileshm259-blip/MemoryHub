# MemoryHub Frontend

Modern, high-performance web application for the **MemoryHub** knowledge management platform. Built with **Next.js 16 (App Router)**, **TypeScript**, and **Tailwind CSS v4**.

---

## Architecture Overview

- **Framework**: Next.js 16 App Router with Turbopack
- **Language**: TypeScript (strict type checking enabled)
- **Styling**: Tailwind CSS v4 with custom SaaS color palette (slate/navy surfaces, indigo accents)
- **API Client**: Centralized, typed fetch wrapper (`src/lib/api.ts`) with Bearer token injection and consistent error handling
- **State Management**: React Context (`src/context/auth-context.tsx`) with automatic token restoration and session expiration handling
- **Layout**: Unified application shell (`src/components/layout/AppShell.tsx`) with responsive sidebar, navigation breadcrumbs, and user profile summary

---

## Getting Started

### 1. Prerequisites

1. Ensure backend infrastructure containers (PostgreSQL and ChromaDB) are running:
   ```powershell
   docker ps
   ```
2. Ensure the FastAPI backend is running on `http://127.0.0.1:8000`:
   ```powershell
   cd backend
   .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
   Verify readiness:
   ```powershell
   curl http://127.0.0.1:8000/health/readiness
   ```

### 2. Frontend Configuration

Create a local environment file in `frontend/` (or copy from `.env.example`):
```powershell
cp .env.example .env.local
```

| Variable | Description | Default Local Value |
| :--- | :--- | :--- |
| `NEXT_PUBLIC_API_BASE_URL` | Base URL for FastAPI backend endpoints | `http://127.0.0.1:8000` |

> [!NOTE]
> Frontend code never contains database credentials, JWT secrets, or production signing keys. Only public environment variables prefixed with `NEXT_PUBLIC_` are exposed to the client bundle.

### 3. Install Dependencies & Run Development Server

```powershell
cd frontend
npm install
npm run dev
```

The application will be accessible at: **`http://localhost:3000`**

---

## Implemented Screens & Feature Status

| Route | Screen Name | Implemented Status | Description |
| :--- | :--- | :---: | :--- |
| `/` | Landing Redirector | ✅ Complete | Checks authentication state; routes authenticated users to `/dashboard` and anonymous visitors to `/login`. |
| `/login` | Sign In | ✅ Complete | Email and password authentication with loading states, form validation, and credential error messaging. |
| `/register` | Create Account | ✅ Complete | Full registration flow (Full Name, Email, Password) with immediate session bootstrap upon account creation. |
| `/dashboard` | User Dashboard | ✅ Complete | Real-time workspace stats (accessible project count), user welcome banner, recent project cards, empty state, and "Create Project" modal. |
| `/projects` | Projects Catalog | ✅ Complete | Full project list with filter/search bar, project cards showing role badges (`Owner`, `Editor`, `Viewer`), and quick actions. |
| `/projects/[id]` | Project Details | ✅ Complete | Deep-dive project workspace with tabbed layout: <br>• **Overview & Settings**: Project metadata, editable description (owner-only), status indicators. <br>• **Team Members**: Membership roster, member email/role display, owner-only "Add Member" modal with live backend validation. <br>• **Handoffs & Sources**: Clearly identified "Coming in Phase 3" state. |
| `/handoffs` | Handoffs | ⏳ Coming Soon | Intentional placeholder explaining upcoming developer handoff functionality with clear roadmap notes. |
| `/sources` | Knowledge Sources | ⏳ Coming Soon | Intentional placeholder explaining upcoming repository and documentation ingestion pipelines. |
| `/integrations` | Integrations | ⏳ Coming Soon | Intentional placeholder detailing planned integrations for Jira, Slack, and GitHub. |

---

## Authentication & Security Model

### Token Storage Strategy
- The JWT access token received upon successful login or registration is held in browser `localStorage` under the key `memoryhub_token`.
- All authenticated API calls made through `src/lib/api.ts` automatically append the HTTP header:
  ```http
  Authorization: Bearer <access_token>
  ```
- Application bootstrap (`auth-context.tsx`) fetches user profile data from `GET /api/auth/me`. If a token is expired, corrupted, or rejected with `401 Unauthorized`, client storage is immediately cleared and the user is redirected to `/login`.

### Security Tradeoffs & Limitations
- **Local Storage vs. HttpOnly Cookies**: Storing access tokens in browser `localStorage` facilitates client-side decoupled routing and rapid local development. However, `localStorage` is vulnerable to Cross-Site Scripting (XSS) if untrusted scripts run in the browser. Migrating to server-issued `HttpOnly`, `SameSite=Lax`, secure cookies is scheduled for production hardening.
- **Client Route Protection**: Client-side route guards (`ProtectedRoute.tsx`) provide responsive UX by shielding dashboard routes from unauthenticated users. Backend authorization remains the sole authoritative gatekeeper for data security.

---

## Verification & Testing Commands

To run all automated frontend checks:

```powershell
cd frontend

# Code style and ESLint rules
npm run lint

# TypeScript compilation and production Next.js bundle build
npm run build
```

To run full backend API test suite:
```powershell
cd ..
backend\.venv\Scripts\python.exe -m pytest backend\tests\ -v
```
