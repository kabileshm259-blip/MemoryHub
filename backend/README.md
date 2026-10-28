# MemoryHub Backend API

FastAPI backend service for MemoryHub with PostgreSQL, Alembic migrations, and ChromaDB integration.

## Prerequisites
- Python 3.11
- Running PostgreSQL container (`memoryhub-postgres` on `127.0.0.1:5432`)
- Running ChromaDB container (`memoryhub-chroma` on `127.0.0.1:8001`)

## Environment Configuration

Configuration variables are read from the repository root `.env` file (copied from `.env.example`):

| Variable | Description | Default Local Value |
| :--- | :--- | :--- |
| `POSTGRES_HOST` | Database host | `127.0.0.1` |
| `POSTGRES_PORT` | Database port | `5432` |
| `POSTGRES_DB` | Database name | `memoryhub` |
| `POSTGRES_USER` | Application user | `memoryhub_user` |
| `POSTGRES_PASSWORD` | Strong local password | *(loaded securely from `.env`)* |
| `CHROMA_URL` | ChromaDB vector service URL | `http://127.0.0.1:8001` |
| `JWT_SECRET` | Secret key for signing JWT tokens (min 32 chars) | *(loaded securely from `.env`)* |
| `JWT_ALGORITHM` | JWT signing algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token time-to-live | `60` |

## Local Setup

1. Create a Python 3.11 virtual environment:
   ```powershell
   py -3.11 -m venv .venv
   ```

2. Upgrade pip and install dependencies:
   ```powershell
   .venv\Scripts\python.exe -m pip install --upgrade pip
   .venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

## Authentication Flow & Token Usage

Authentication uses JSON Web Tokens (JWT) signed using HMAC-SHA256 (`HS256`) and passwords hashed with `bcrypt` (12 salt rounds).

1. **Registration (`POST /api/auth/register`)**:
   - Accepts `email`, `password` (8-72 characters), and `display_name`.
   - Normalizes email (lowercased and whitespace stripped).
   - Generates a bcrypt password hash stored in the `users` table. Never logs or echoes the plaintext password.
   - Returns public user profile (excluding `password_hash`).

2. **Login (`POST /api/auth/login`)**:
   - Accepts `email` and `password`.
   - Returns generic `401 Unauthorized` errors to prevent account enumeration.
   - On success, returns `{ "access_token": "<jwt>", "token_type": "bearer", "expires_in": 3600 }`.

3. **Authenticated Requests**:
   - Include the token in the HTTP Authorization header:
     ```http
     Authorization: Bearer <access_token>
     ```
   - FastAPI dependencies validate token signature, expiration (`exp`), and subject UUID (`sub`).
   - The user identity is resolved entirely server-side; request body user IDs are never trusted as proof of identity.

## Role Permissions & Authorization Rules

MemoryHub enforces server-side role-based access control for projects:

| Action | Owner | Editor | Viewer | Non-Member |
| :--- | :---: | :---: | :---: | :---: |
| Read Project (`GET /api/projects/{id}`) | ✅ | ✅ | ✅ | ❌ (404 Not Found) |
| List Members (`GET /api/projects/{id}/members`) | ✅ | ✅ | ✅ | ❌ (404 Not Found) |
| Update Project Settings (`PATCH /api/projects/{id}`) | ✅ | ❌ (403 Forbidden) | ❌ (403 Forbidden) | ❌ (404 Not Found) |
| Add Members (`POST /api/projects/{id}/members`) | ✅ | ❌ (403 Forbidden) | ❌ (403 Forbidden) | ❌ (404 Not Found) |

### Information Leakage Prevention Policy
- Non-members receive `404 Not Found` when accessing private projects or attempting member management, ensuring project existence is not disclosed to unauthorized users.
- Project membership uniqueness is enforced both pre-emptively and via the database constraint (`uq_project_membership_user_project`), safely returning `409 Conflict` on duplicates.

## API Endpoint Overview

| Method | Endpoint | Auth Required | Description |
| :--- | :--- | :---: | :--- |
| `GET` | `/` | No | API root welcome message and version |
| `GET` | `/health` / `/health/liveness` | No | Process liveness probe |
| `GET` | `/health/readiness` / `/ready` | No | Readiness probe (PostgreSQL and ChromaDB) |
| `POST` | `/api/auth/register` | No | Register a new user account |
| `POST` | `/api/auth/login` | No | Login and obtain JWT access token |
| `GET` | `/api/auth/me` | Bearer Token | Retrieve currently authenticated user profile |
| `POST` | `/api/projects` | Bearer Token | Create project; assign caller as `owner` |
| `GET` | `/api/projects` | Bearer Token | List caller's projects (supports `limit`, `offset`) |
| `GET` | `/api/projects/{project_id}` | Bearer Token | Get project details (members only) |
| `PATCH` | `/api/projects/{project_id}` | Bearer Token | Update project name/description/status (owners only) |
| `GET` | `/api/projects/{project_id}/members` | Bearer Token | List project members (members only) |
| `POST` | `/api/projects/{project_id}/members` | Bearer Token | Add an existing user by email (owners only) |
| `GET` | `/docs` | No | Interactive Swagger OpenAPI UI |

## Database Schema & Migrations (Alembic)

Migrations are managed with Alembic under [`alembic/`](alembic/):

- **Current Migration Revision**: `01ba3083209e` (`add_user_password_hash`)
- **Apply migrations**:
  ```powershell
  .venv\Scripts\alembic.exe upgrade head
  ```
- **Inspect current revision**:
  ```powershell
  .venv\Scripts\alembic.exe current
  ```
- **Check for schema drift**:
  ```powershell
  .venv\Scripts\alembic.exe check
  ```

### Safe Database Practices
- Never hardcode connection credentials in `alembic.ini` or migration scripts.
- Never run destructive commands like `Base.metadata.drop_all()`, `docker compose down -v`, or table truncations on the development database.
- Always run `alembic check` before committing schema modifications.

## Automated Testing

Tests are located in [`tests/`](tests/) and use a dedicated test database (`memoryhub_test`) with transactional savepoints for complete isolation without altering or truncating tables.

Run the test suite:
```powershell
.venv\Scripts\python.exe -m pytest tests/ -v
```

Test coverage includes:
1. Registration succeeds with valid data.
2. Duplicate registration is rejected (409 Conflict).
3. Passwords stored only as bcrypt hashes.
4. Login succeeds with correct credentials.
5. Login fails with incorrect credentials (generic 401).
6. Expired, tampered, or invalid tokens rejected.
7. Authenticated users create and list their own projects.
8. Project owners can add members with designated roles.
9. Non-owners cannot add members or change settings (403 Forbidden).
10. Non-members cannot read private projects (404 Not Found).
11. Viewers cannot perform editing operations (403 Forbidden).
12. Duplicate memberships handled safely (409 Conflict).
13. Health and readiness endpoints remain functional.

## Local Development Security Limitations

This authentication system is designed for local development and demonstration:
- **No Token Revocation / Blacklist**: JWT tokens remain valid until expiration. Immediate session revocation on logout would require a token revocation blocklist (e.g. Redis).
- **Single Secret Key**: Symmetric HMAC-SHA256 signing is used instead of asymmetric key pairs (e.g., RS256/EdDSA) or an external OIDC/OAuth2 identity provider.
- **No Refresh Token Rotation**: Only access tokens are issued. Long-lived sessions with refresh token rotation and client binding are not implemented.
- **No Email Verification**: Accounts are activated immediately upon registration without email confirmation.
- **No Rate Limiting**: Brute-force protection on login/registration is not included in this phase.
