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

1. Crea una base PostgreSQL en el proyecto.
2. Define `API_KEY` y `DATABASE_URL` como variables privadas del entorno; nunca las escribas en el código ni las registres.
3. Copia las demás variables de `.env.example` según necesites.
4. El workflow del proyecto arranca `uvicorn` con el puerto que Replit proporciona.

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
DATABASE_URL=postgresql://usuario:password@host:5432/bloxen
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