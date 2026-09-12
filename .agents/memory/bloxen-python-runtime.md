---
name: Bloxen Python runtime
description: Runtime constraints discovered while moving the API artifact from the TypeScript scaffold to FastAPI.
---

Artifact-owned API workflows execute with the artifact directory as their working directory, so commands must reference local files and modules directly rather than changing into `artifacts/api-server`.

**Why:** A workflow command with an extra `cd artifacts/api-server` failed because the managed runner had already selected that directory.

Replit PostgreSQL URLs may contain libpq parameters such as `sslmode` and `channel_binding` that asyncpg does not accept as connection keyword arguments. Remove those query keys and map `sslmode` to asyncpg's `ssl` connect argument before creating the SQLAlchemy engine.

**Why:** Passing `sslmode` directly caused the application to fail during startup before any route was available.

**How to apply:** Keep PostgreSQL as the production database, preserve a clear degraded health response when the configured database is unavailable, and never log the URL or credentials.

Render's Python 3.14 default can fail while SQLAlchemy scans `Mapped[T | None]` annotations; nullable ORM columns should use non-union `Mapped[T]` types with `nullable=True`.

**Why:** The union annotation failure happens during model import, before Uvicorn starts; removing the union from SQLAlchemy's mapped attribute annotation preserves the database schema and keeps Render's default runtime.

**How to apply:** Keep PEP 604 unions in non-ORM code as needed, but avoid them specifically on SQLAlchemy `Mapped` fields that are nullable.