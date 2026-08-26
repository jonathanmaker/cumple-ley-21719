# cumple21719

Software open source de cumplimiento de la **Ley 21.719** (protección de datos personales, Chile), pensado para que emprendedores, PYMEs y empresas de cualquier tamaño puedan autoalojarlo y entrar en cumplimiento sin depender de un proveedor externo.

No está pensado para ser hosteado ni vendido como servicio por sus autores: cada organización despliega su propia instancia con su propia base de datos.

## Estado actual

En desarrollo activo. Ya construido y probado de punta a punta (`docker compose up --build` desde cero, y con pruebas funcionales reales — no solo `check`): modelo de datos del núcleo, cifrado de campos sensibles (AES-256-GCM), la API REST de integración (`/api/v1/`), despacho de webhooks salientes con firma HMAC y reintento, el motor de retención/anonimización, y un frontend mínimo real (portal interno + wizard de onboarding + formulario público de ARCO) además del admin de Django.

**Pendiente:** pantallas adicionales del portal (hoy solo cubre organización/RAT vía wizard y la cola de ARCO; el resto de catálogos del RAT se administra desde `/admin/`), scheduler/cron real para `aplicar_retencion` y `reintentar_webhooks` (hoy son comandos manuales, ver más abajo), diseño visual (el CSS actual es funcional, no definitivo).

## Stack

- **Backend:** Django 5.1 (Python 3.12).
- **Base de datos:** PostgreSQL 16.
- **Despliegue:** Docker Compose (`docker compose up`), pensado para correr en cualquier VPS económico.
- **Licencia:** [AGPL-3.0](./LICENSE) — si alguien ofrece este software como servicio hosteado, sus modificaciones también deben liberarse.

## Arquitectura

Monolito modular: cada dominio del cumplimiento vive en su propia app Django bajo `apps/`, y todas comparten una única base de datos.

| App | Responsabilidad |
|---|---|
| `apps.organizacion` | Datos de la entidad responsable del tratamiento (Art. 2 letra ll) y su DPD. |
| `apps.usuarios` | Perfil de usuarios internos; roles vía Groups/Permissions nativos de Django. |
| `apps.rat` | Registro de Actividades de Tratamiento — plantillas por rubro, tipos de dato, destinatarios, medidas de seguridad. |
| `apps.titulares` | Personas naturales dueñas de los datos tratados (registro delgado). |
| `apps.consentimiento` | Políticas de privacidad versionadas y registro de consentimiento otorgado/revocado. |
| `apps.arco` | Solicitudes de derechos ARCO + Portabilidad + Bloqueo, con SLA de 30 días. |
| `apps.auditoria` | Bitácora de auditoría inmutable (solo inserción). |
| `apps.integraciones` | Sistemas legados conectados vía API, contratos de encargado (Art. 15 bis) y webhooks salientes. |
| `apps.portal` | Frontend interno (login, dashboard, wizard de onboarding, cola de solicitudes ARCO) + formulario público de ARCO para PYMEs sin sistema legado integrado. |

Cada modelo referencia en su docstring el documento legal o de skill del que salió (`CTX-00X`, `SKL-XXX-00X`) — ver el framework de desarrollo en el repo hermano de este proyecto para el detalle completo.

`apps.api` es la app transversal que expone `/api/v1/` para que sistemas legados (CRM, ERP, sitio web propio del cliente) se acoplen sin migrar a esta plataforma — ver sección siguiente.

## API de integración

Pensada para que un sistema legado del cliente (WordPress, un ERP propio, etc.) se conecte sin tener que migrar sus datos a esta plataforma.

- **Documentación interactiva:** `http://localhost:8000/api/v1/docs/` (pública, no requiere API key).
- **Autenticación:** cabecera `Authorization: Api-Key <token>`. La key se genera una sola vez vía `SistemaIntegrado.crear_con_api_key(nombre=..., scopes=[...])` — solo se persiste su hash, así que no hay forma de recuperarla después; hay que guardarla en el momento.
- **Scopes disponibles:** `titulares:read`/`write`, `consentimiento:read`/`write`, `arco:read`/`write`, `auditoria:write`. Sin el scope exacto para la acción, la API responde `403` aunque la key sea válida.
- **Endpoints principales:** `POST /api/v1/titulares/` (alta/actualización por RUT), `POST /api/v1/consentimientos/` + `POST /api/v1/consentimientos/{id}/revocar/`, `POST /api/v1/solicitudes-arco/` (calcula automáticamente el plazo de 30 días), `POST /api/v1/auditoria/` (el sistema externo registra sus propios eventos en la misma bitácora inmutable).
- El RUT nunca se devuelve en una respuesta de la API — es un campo de solo escritura; la correlación se hace por `id`.
- Toda escritura vía API queda automáticamente en `apps.auditoria.AuditLog`, atribuida al `SistemaIntegrado` que la hizo.

## Webhooks salientes y retención de datos

- **Webhooks:** cuando se revoca un consentimiento, se resuelve una solicitud ARCO, o el motor de retención anonimiza a un titular, se notifica (POST + firma HMAC-SHA256 en `X-Cumple21719-Firma`) a todo `WebhookSuscripcion` activo suscrito a ese evento — sin importar qué sistema originó el dato, porque varios sistemas legados de la misma organización pueden compartir el mismo titular. Envío síncrono y best-effort (sin cola de tareas, para no sumar otro servicio a la pila); los fallos quedan en `WebhookEntrega` con `entregado=False`.
- **Reintento:** `python manage.py reintentar_webhooks` reintenta las entregas fallidas (hasta 5 intentos). No hay scheduler propio — se ejecuta vía cron externo del hosting/VPS.
- **Retención:** `python manage.py aplicar_retencion` (con `--dry-run` para previsualizar) anonimiza titulares cuyo consentimiento fue revocado y ya venció el plazo de conservación de esa actividad, siempre que no tengan otro consentimiento vigente. Alcance deliberadamente acotado al caso "consentimiento revocado + plazo vencido" (Art. 7 letra b) — relaciones que terminan por otras vías (fin de contrato, término laboral) no están cubiertas todavía, ver el docstring del comando.

## Desarrollo local

```bash
cp .env.example .env      # ajustar valores
docker compose up --build
```

La app queda disponible en `http://localhost:8000`. `docker compose` aplica migraciones automáticamente al iniciar.

- Portal (login requerido): `http://localhost:8000/`
- Formulario público de ARCO: `http://localhost:8000/solicitudes-arco/nueva/`
- Administración: `http://localhost:8000/admin/`
- Docs de la API: `http://localhost:8000/api/v1/docs/`

Crear el primer usuario de acceso al portal/admin:

```bash
docker compose exec web python manage.py createsuperuser
```

Para desarrollo sin Docker (usa SQLite si no defines `POSTGRES_DB` en el entorno):

```bash
python -m venv .venv
source .venv/bin/activate  # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Licencia

AGPL-3.0 — ver [LICENSE](./LICENSE).
