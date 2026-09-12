---
name: Bloxen Python runtime
description: Runtime constraints discovered while moving the API artifact from the TypeScript scaffold to FastAPI.
---

Artifact-owned API workflows execute with the artifact directory as their working directory, so commands must reference local files and modules directly rather than changing into `artifacts/api-server`.

**Why:** A workflow command with an extra `cd artifacts/api-server` failed because the managed runner had already selected that directory.

Replit PostgreSQL URLs may contain libpq parameters such as `sslmode` and `channel_binding` that asyncpg does not accept as connection keyword arguments. Remove those query keys and map `sslmode` to asyncpg's `ssl` connect argument before creating the SQLAlchemy engine.

**Why:** Passing `sslmode` directly caused the application to fail during startup before any route was available.

**How to apply:** Keep PostgreSQL as the production database, preserve a clear degraded health response when the configured database is unavailable, and never log the URL or credentials.

Render's current Python 3.14 default is incompatible with the SQLAlchemy declarative union annotations used by this API; keep Render on Python 3.13 until that upstream typing behavior is resolved.

**Why:** Python 3.14 caused SQLAlchemy model imports to fail before Uvicorn could start, while the same code passes on Python 3.13.

**How to apply:** Pin the service with `.python-version` and/or `PYTHON_VERSION=3.13.11`, then use Render's normal Uvicorn start command.