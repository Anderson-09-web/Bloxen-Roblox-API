---
name: Bloxen Python runtime
description: Runtime constraints discovered while moving the API artifact from the TypeScript scaffold to FastAPI.
---

Artifact-owned API workflows execute with the artifact directory as their working directory, so commands must reference local files and modules directly rather than changing into `artifacts/api-server`.

**Why:** A workflow command with an extra `cd artifacts/api-server` failed because the managed runner had already selected that directory.

Replit PostgreSQL URLs may contain libpq parameters such as `sslmode` and `channel_binding` that asyncpg does not accept as connection keyword arguments. Remove those query keys and map `sslmode` to asyncpg's `ssl` connect argument before creating the SQLAlchemy engine.

**Why:** Passing `sslmode` directly caused the application to fail during startup before any route was available.

**How to apply:** Keep PostgreSQL as the production database, preserve a clear degraded health response when the configured database is unavailable, and never log the URL or credentials.

When the workspace runtime and artifact runtime use different Python versions, install and test through the artifact's own `pyproject.toml`; native SQLAlchemy dependencies can fail to load under the mixed environment. The managed preview should invoke that project environment explicitly.

**Why:** The workspace's default Python 3.12 environment did not see packages installed for Python 3.14, while SQLAlchemy's compiled greenlet extension also required the matching runtime libraries.

**How to apply:** Keep Render's `requirements.txt` commands unchanged, but use the artifact project runner for local preview verification when the managed workflow and workspace interpreter disagree.

Render's Python 3.14 default can fail while SQLAlchemy scans `Mapped[T | None]` annotations; nullable ORM columns should use non-union `Mapped[T]` types with `nullable=True`.

**Why:** The union annotation failure happens during model import, before Uvicorn starts; removing the union from SQLAlchemy's mapped attribute annotation preserves the database schema and keeps Render's default runtime.

**How to apply:** Keep PEP 604 unions in non-ORM code as needed, but avoid them specifically on SQLAlchemy `Mapped` fields that are nullable.