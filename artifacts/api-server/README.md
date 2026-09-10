# Bloxen Roblox API

API REST asíncrona para el bot de Discord Bloxen. Resuelve usuarios Roblox, verifica perfiles con códigos temporales, vincula cuentas Discord ↔ Roblox y calcula cambios de presencia sin modificar Discord.

## Requisitos

- Python 3.12 o superior.
- PostgreSQL 14 o superior para producción.
- Acceso de salida HTTPS a las APIs públicas oficiales de Roblox.

La aplicación usa FastAPI, Uvicorn, `httpx.AsyncClient` y SQLAlchemy async con `asyncpg`. No usa Node.js.

## Ejecutar localmente

```bash
cd artifacts/api-server
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
# Edita API_KEY y DATABASE_URL
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Para un arranque local sin PostgreSQL, si `DATABASE_URL` queda vacío se usa SQLite async como fallback. En producción configura PostgreSQL siempre.

## Replit

### 1. Configura Secrets

En el panel **Secrets** del proyecto añade:

| Nombre | Tipo | Uso |
|---|---|---|
| `API_KEY` | Secret | Bearer token que usará Bloxen |
| `BLOXEN_DATABASE_URL` | Secret | Connection string de PostgreSQL Neon |

`BLOXEN_DATABASE_URL` tiene prioridad sobre la variable automática `DATABASE_URL` de Replit. No guardes estos valores en `.env`, GitHub, el README ni el código.

La URL de Neon debe ser una connection string nueva después de rotar la contraseña del rol si la anterior fue compartida en el chat. La aplicación acepta URLs con `sslmode=require` y `channel_binding=require`.

### 2. Configura variables normales

En **Environment variables** puedes usar:

```env
PRESENCE_INTERVAL=60
CACHE_TTL=30
CORS_ORIGINS=*
ENVIRONMENT=production
ROBLOX_TIMEOUT=8
ROBLOX_RETRIES=2
VERIFICATION_TTL=600
VERIFICATION_MAX_ATTEMPTS=5
RATE_LIMIT_MAX_REQUESTS=120
RATE_LIMIT_WINDOW_SECONDS=60
```

### 3. Prueba antes de publicar

El workflow de Replit ya está configurado para ejecutar:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
```

Comprueba:

```bash
curl https://TU-DOMINIO-DEV/health
curl https://TU-DOMINIO-DEV/docs
curl -H "Authorization: Bearer TU_API_KEY" \
  https://TU-DOMINIO-DEV/api/v1/roblox/user/Builderman
```

`/health` debe devolver `"database": "ok"`. Si devuelve `"database": "unavailable"`, no publiques todavía: Neon sigue rechazando la credencial.

### 4. Publica

1. Abre la herramienta **Publishing**.
2. Usa la configuración de producción del artifact.
3. Para mantener activo el polling periódico, elige un despliegue que mantenga el proceso encendido, como **VM**. Si el bot de Discord llama directamente a `/presence/check` y no dependes del polling interno, Autoscale también es válido.
4. Publica y espera a que el health check `/health` sea correcto.
5. Usa la URL `https://...replit.app` publicada como base para Bloxen. No uses la URL `.replit.dev` en el bot.

El arranque de producción ya está configurado con Uvicorn, el puerto `8080` y el health check `/health`.

## Render y VPS

Build:

```bash
python -m pip install -r artifacts/api-server/requirements.txt
```

Start:

```bash
cd artifacts/api-server && python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

Variables mínimas:

```env
API_KEY=una-clave-larga-y-aleatoria
BLOXEN_DATABASE_URL=postgresql://usuario:password@host.neon.tech/bloxen?sslmode=require
PRESENCE_INTERVAL=60
CACHE_TTL=30
CORS_ORIGINS=*
ENVIRONMENT=production
```

Las tablas se crean al iniciar. Para despliegues con migraciones formales, el esquema está centralizado en `app/database/models.py` y puede migrarse después con Alembic sin cambiar los contratos.

## Autenticación y seguridad

Todas las rutas `/api/v1/*` requieren:

```http
Authorization: Bearer API_KEY
```

La API incluye:

- Comparación constante de la API key.
- Rate limiting en memoria por IP y ruta; configurable con `RATE_LIMIT_MAX_REQUESTS` y `RATE_LIMIT_WINDOW_SECONDS`.
- Validación Pydantic y protección contra inyección mediante SQLAlchemy parametrizado.
- Timeout y reintentos limitados para Roblox.
- Caché TTL para usuarios y juegos.
- Códigos de verificación de un solo uso, con expiración de 10 minutos y límite de intentos.
- CORS configurable.
- Errores genéricos para el cliente y logs sin API keys ni tokens.

El rate limiter es por proceso. Si se ejecutan varias réplicas, coloca un límite distribuido delante de la API (por ejemplo, el proxy del proveedor) o sustituye el middleware por Redis.

## Endpoints

Públicos:

- `GET /` — información de la API.
- `GET /health` — estado del proceso y de la base de datos.
- `GET /docs` — Swagger UI.

Privados:

- `GET /api/v1/roblox/user/{username}` — lookup público de usuario, descripción, avatar y fecha de creación.
- `POST /api/v1/roblox/verify/create` — body `{ "discord_id": "...", "username": "..." }`.
- `POST /api/v1/roblox/verify/check` — body `{ "discord_id": "...", "code": "BLOXEN-..." }`.
- `POST /api/v1/roblox/link` — reusa un vínculo ya verificado.
- `DELETE /api/v1/roblox/unlink` — body `{ "discord_id": "..." }`.
- `GET /api/v1/roblox/presence/{roblox_id}` — estado actual de presencia.
- `POST /api/v1/roblox/presence/check` — body `{ "discord_id": "...", "guild_id": "...", "roblox_id": 123 }`.
- `GET /api/v1/discord/verify/config/{guild_id}`.
- `PUT /api/v1/discord/verify/config/{guild_id}` — body `{ "verified_role_id": "...", "enabled": true }`.

## Flujo de verificación

1. Bloxen solicita `verify/create` con el username de Roblox.
2. La API resuelve el username a un ID y devuelve un código `BLOXEN-XXXXXX`.
3. El usuario copia el código a la descripción pública de su perfil.
4. Bloxen llama a `verify/check`.
5. La API consulta el perfil por ID, comprueba la descripción, marca la cuenta como verificada e invalida el código.
6. Bloxen puede entregar el rol configurado al usuario. Si ya está verificado, no se debe pedir otro código.

El ID se fija al crear el código y se verifica contra el perfil, por lo que no se confía solamente en el username.

## Presencia y nicknames

`POST /presence/check` devuelve el estado y una acción, pero nunca modifica Discord:

```json
{
  "status": "playing",
  "game_name": "Grow a Garden",
  "place_id": "123",
  "universe_id": "456",
  "game_icon": null,
  "changed": true,
  "action": "update_nickname",
  "guild_id": "777",
  "roblox_id": 12345
}
```

Acciones posibles:

- `update_nickname`: el bot puede usar `🌱 Nombre • Juego` o el emoji que corresponda.
- `reset_nickname`: el bot debe restaurar el nombre normal.
- `null`: no hubo cambio; no repetir respuestas.

El bot `discord.py` es el único responsable de `Member.edit(nick=...)`, siempre limitado al `guild_id` indicado. La API no contiene código para modificar Discord.

## Base de datos

Se crean estas tablas con índices y restricciones:

- `roblox_accounts`
- `verification_codes`
- `presence_configs`
- `guild_verification_configs`

Los campos principales y la relación de estados se encuentran en `app/database/models.py`.

## Tests

```bash
cd artifacts/api-server
python -m pytest -q
```

Los tests usan `httpx.MockTransport`; no llaman a Roblox. Cubren autenticación, generación y expiración de códigos, verificación, linking/unlink, lookup, presencia, cambios repetidos, configuración de guild y límite de solicitudes.