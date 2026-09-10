# Bloxen Roblox API

API REST asíncrona para que el bot de Discord Bloxen verifique cuentas Roblox y consulte su presencia sin modificar Discord.

## Run & Operate

- `cd artifacts/api-server && python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}` — ejecutar la API
- `cd artifacts/api-server && python -m pytest -q` — ejecutar tests
- El workflow `artifacts/api-server: API Server` arranca la API con Uvicorn.
- Variables requeridas en producción: `API_KEY` y `DATABASE_URL`.

## Stack

- Python 3.12+, FastAPI, Uvicorn, httpx async
- PostgreSQL + SQLAlchemy async + asyncpg
- Validación: Pydantic
- API pública oficial de Roblox

## Where things live

- `artifacts/api-server/app/main.py` — aplicación FastAPI, middleware y ciclo de vida
- `artifacts/api-server/app/api/routes/` — endpoints
- `artifacts/api-server/app/services/` — Roblox, verificación y presencia
- `artifacts/api-server/app/database/models.py` — tablas e índices SQLAlchemy
- `artifacts/api-server/README.md` — instalación, variables y contratos para el bot

## Architecture decisions

- La API nunca cambia nicknames ni llama a Discord; devuelve `action` para que `discord.py` actúe en el guild seleccionado.
- La verificación fija el `roblox_id` al generar el código y luego comprueba la descripción por ID, no solo por username.
- PostgreSQL es la base de producción; SQLite async solo se usa como fallback local cuando no hay `DATABASE_URL`.
- El rate limiter es por proceso; en varias réplicas se debe complementar con un límite distribuido.

## Product

Permite lookup público de Roblox, códigos de verificación de un solo uso, vínculo Discord ↔ Roblox, presencia con detección de cambios de juego y configuración de roles de verificación por guild.

## User preferences

- La API debe ser Python 3.12+ y completamente asíncrona; no se usa Node.js en el servidor Bloxen.

## Gotchas

- Configurar `API_KEY` y `DATABASE_URL` antes de usar rutas `/api/v1/*`.
- Los cambios de presencia no se aplican en Discord desde la API; el bot debe interpretar `update_nickname` y `reset_nickname`.

## Pointers

- La documentación operativa está en `artifacts/api-server/README.md`.
