from __future__ import annotations

from html import escape


OPENAPI_DESCRIPTION = """
## Bloxen Roblox API

API REST para el bot de Discord Bloxen.

### Inicio rápido

1. Abre `GET /` para ver la guía web.
2. Abre `GET /health` para comprobar la base de datos.
3. Usa `Authorization: Bearer API_KEY` en todas las rutas `/api/v1/*`.
4. Consulta los esquemas y prueba requests desde Swagger en `/docs`.

### Flujo de verificación

- `POST /api/v1/roblox/verify/create` genera un código temporal.
- El usuario coloca el código en la descripción pública de Roblox.
- `POST /api/v1/roblox/verify/check` confirma el código y guarda el vínculo.
- La API no modifica Discord; el bot `discord.py` ejecuta los cambios de nickname y roles.

### Persistencia

Las rutas de verificación, linking, presencia y configuración requieren PostgreSQL.
Si la base de datos no está disponible, responden `503` en lugar de ocultar el problema con un `500`.
"""

OPENAPI_TAGS = [
    {"name": "System", "description": "Estado del servicio y guía pública."},
    {"name": "Roblox", "description": "Usuarios Roblox y verificación Discord ↔ Roblox."},
    {"name": "Presence", "description": "Presencia Roblox y acciones que el bot puede aplicar."},
    {"name": "Discord verification", "description": "Configuración de verificación por servidor."},
]


def build_landing_page(version: str, environment: str, database_available: bool) -> str:
    status_label = "Conectada" if database_available else "No disponible"
    status_class = "ok" if database_available else "warning"
    database_note = (
        "Las rutas que guardan datos están listas."
        if database_available
        else "Configura una contraseña válida de PostgreSQL para activar verificación, linking y presencia."
    )
    safe_version = escape(version)
    safe_environment = escape(environment)
    safe_status = escape(status_label)
    safe_note = escape(database_note)

    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Guía y documentación de Bloxen Roblox API">
  <title>Bloxen Roblox API · v{safe_version}</title>
  <style>
    :root {{ color-scheme: dark; --bg: #0b1020; --panel: #121a2f; --muted: #9eabc8; --text: #f5f7ff; --accent: #7c9cff; --line: #263352; --ok: #49d39c; --warn: #ffca6b; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: radial-gradient(circle at 10% 0%, #1b2850 0, var(--bg) 42%); color: var(--text); font: 16px/1.6 Inter, ui-sans-serif, system-ui, -apple-system, sans-serif; }}
    main {{ width: min(1100px, calc(100% - 32px)); margin: 0 auto; padding: 56px 0 72px; }}
    .hero {{ display: flex; justify-content: space-between; gap: 28px; align-items: end; margin-bottom: 30px; }}
    h1 {{ font-size: clamp(2.1rem, 5vw, 4rem); line-height: 1; letter-spacing: -.05em; margin: 12px 0; }}
    h2 {{ margin: 0 0 12px; font-size: 1.2rem; }}
    p {{ color: var(--muted); margin: 8px 0; }}
    .eyebrow {{ color: var(--accent); font-weight: 750; letter-spacing: .12em; text-transform: uppercase; font-size: .78rem; }}
    .version {{ color: var(--muted); font-weight: 650; }}
    .actions {{ display: flex; flex-wrap: wrap; gap: 10px; }}
    a.button {{ display: inline-block; padding: 11px 16px; border-radius: 10px; color: #081020; background: var(--accent); font-weight: 750; text-decoration: none; }}
    a.button.secondary {{ background: transparent; color: var(--text); border: 1px solid var(--line); }}
    .grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }}
    .card {{ background: color-mix(in srgb, var(--panel) 92%, transparent); border: 1px solid var(--line); border-radius: 16px; padding: 22px; box-shadow: 0 18px 50px #05091455; }}
    .wide {{ grid-column: 1 / -1; }}
    .status {{ display: inline-flex; align-items: center; gap: 8px; font-weight: 750; }}
    .status::before {{ content: ""; width: 9px; height: 9px; border-radius: 50%; background: currentColor; }}
    .status.ok {{ color: var(--ok); }} .status.warning {{ color: var(--warn); }}
    code, pre {{ font: .91rem/1.6 ui-monospace, SFMono-Regular, Menlo, monospace; }}
    code {{ color: #cbd7ff; }} pre {{ overflow-x: auto; padding: 16px; border-radius: 10px; background: #080d1b; border: 1px solid var(--line); color: #dce5ff; }}
    ul {{ padding-left: 20px; color: var(--muted); }} li + li {{ margin-top: 7px; }}
    .endpoint {{ display: grid; grid-template-columns: 74px 1fr; gap: 12px; padding: 12px 0; border-top: 1px solid var(--line); }}
    .method {{ color: var(--ok); font: 700 .82rem ui-monospace, monospace; }}
    footer {{ color: var(--muted); margin-top: 24px; font-size: .9rem; }}
    @media (max-width: 720px) {{ .hero, .grid {{ display: block; }} .actions {{ margin-top: 20px; }} .card {{ margin-top: 16px; }} }}
  </style>
</head>
<body>
<main>
  <section class="hero">
    <div>
      <div class="eyebrow">Bloxen · Roblox Developer API</div>
      <h1>Roblox API para Discord</h1>
      <p class="version">Versión <strong>{safe_version}</strong> · Entorno <strong>{safe_environment}</strong></p>
    </div>
    <div class="actions">
      <a class="button" href="/docs">Abrir Swagger</a>
      <a class="button secondary" href="/redoc">Abrir ReDoc</a>
    </div>
  </section>

  <section class="grid">
    <article class="card">
      <h2>Estado de la API</h2>
      <div class="status {status_class}">Base de datos: {safe_status}</div>
      <p>{safe_note}</p>
      <p>Health check: <a href="/health"><code>/health</code></a></p>
    </article>
    <article class="card">
      <h2>Autenticación</h2>
      <p>Todas las rutas <code>/api/v1/*</code> requieren un token Bearer.</p>
      <pre>Authorization: Bearer TU_API_KEY</pre>
    </article>

    <article class="card wide">
      <h2>Flujo recomendado de verificación</h2>
      <ol>
        <li>El bot llama a <code>POST /api/v1/roblox/verify/create</code>.</li>
        <li>El usuario copia el código recibido en la descripción pública de Roblox.</li>
        <li>El bot llama a <code>POST /api/v1/roblox/verify/check</code>.</li>
        <li>El bot asigna el rol o cambia el nickname en Discord. Esta API nunca modifica Discord directamente.</li>
      </ol>
      <pre>curl -X POST https://TU-DOMINIO/api/v1/roblox/verify/create \
  -H "Authorization: Bearer TU_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{{"discord_id":"9001","username":"Builderman"}}'</pre>
    </article>

    <article class="card wide">
      <h2>Endpoints principales</h2>
      <div class="endpoint"><span class="method">GET</span><code>/api/v1/roblox/user/{{username}}</code></div>
      <div class="endpoint"><span class="method">POST</span><code>/api/v1/roblox/verify/create</code></div>
      <div class="endpoint"><span class="method">POST</span><code>/api/v1/roblox/verify/check</code></div>
      <div class="endpoint"><span class="method">POST</span><code>/api/v1/roblox/presence/check</code></div>
      <div class="endpoint"><span class="method">GET</span><code>/api/v1/discord/verify/config/{{guild_id}}</code></div>
      <p>Swagger contiene los schemas, parámetros, cuerpos JSON y respuestas de cada endpoint.</p>
    </article>
  </section>
  <footer>La documentación interactiva está disponible en <a href="/docs"><code>/docs</code></a>. La API no almacena API keys en respuestas ni en logs.</footer>
</main>
</body>
</html>"""