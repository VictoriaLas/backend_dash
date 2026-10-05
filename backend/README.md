# VM Dashboard · Backend (FastAPI)

API del dashboard de máquinas virtuales: login con JWT en cookie HttpOnly, roles **Administrador** y **Cliente**, y CRUD de VMs sobre SQLite.

## Arranque rápido

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env        # y cambia VMD_JWT_SECRET
uvicorn app.main:app --reload
```

- Swagger: http://localhost:8000/docs (haz `POST /login` ahí mismo; la cookie se guarda y las siguientes peticiones ya van autenticadas).
- Tests: `pytest`

Usuarios de ejemplo que se crean la primera vez:

| Email | Contraseña | Rol |
|---|---|---|
| `admin@vmdashboard.com` | `admin123` | Administrador |
| `cliente@vmdashboard.com` | `cliente123` | Cliente |

## Autenticación

- `POST /login` con `{"email", "password"}` valida las credenciales y responde con `Set-Cookie: access_token=<JWT>; HttpOnly; Secure; SameSite=Lax; Max-Age=3600; Path=/`.
- El body devuelve **solo** el usuario y su rol: `{"id", "email", "name", "role": "Administrador" | "Cliente"}`. El token nunca aparece en el body.
- `JWTCookieMiddleware` (`app/middleware.py`) valida la cookie en cada petición que no sea pública y responde 401 si falta, está manipulada o ha expirado. No acepta tokens en la cabecera `Authorization`.
- El rol se lee de la base de datos en cada petición (no del token), así que un cambio de rol o un usuario desactivado tiene efecto inmediato.
- Contraseñas con bcrypt. El login tarda lo mismo exista o no el email.

## Endpoints

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| POST | `/login` | Público | Valida email y password, pone la cookie y devuelve usuario + rol |
| POST | `/logout` | Público | Borra la cookie (204) |
| GET | `/me` | Admin, Cliente | Usuario de la sesión actual (útil al recargar la página) |
| GET | `/vms` | Admin, Cliente | Lista de VMs. Filtros opcionales: `status`, `search` (nombre u OS) |
| GET | `/vms/{id}` | Admin, Cliente | Detalle de una VM |
| POST | `/vms` | **Solo Admin** | Crea una VM: `name`, `cores`, `ram`, `disk`, `os`, `status` (201) |
| PUT | `/vms/{id}` | **Solo Admin** | Actualiza los campos enviados (los omitidos se mantienen) |
| DELETE | `/vms/{id}` | **Solo Admin** | Elimina la VM (204) |
| GET | `/summary` | Admin, Cliente | KPIs: VMs por estado y por OS, totales de cores/RAM/disco y los de las VMs activas (`running_cores`, `running_ram`, `running_disk`) |
| GET | `/vms/{id}/metrics?range=1h` | Admin, Cliente | Serie de CPU/RAM/disco **simulada** para gráficas (`1h`, `6h`, `24h`, `7d`) |
| GET / POST | `/users` | **Solo Admin** | Listar / crear usuarios (`email`, `name`, `password`, `role`) |
| GET | `/health` | Público | Estado de la API |
| WS | `/ws` | Admin, Cliente | Eventos en tiempo real de cambios en las VMs (ver abajo) |

Respuestas de error: 401 sin sesión o sesión inválida, 403 rol insuficiente, 404 VM inexistente, 409 nombre de VM o email repetido, 422 datos no válidos.

### Modelo de VM

| Campo | Tipo | Notas |
|---|---|---|
| `name` | string | Único (sin distinguir mayúsculas). 2 a 63 caracteres, empieza por letra o número; solo letras, números, `.`, `-` y `_` |
| `cores` | int | 1 a 256 |
| `ram` | int | GB |
| `disk` | int | GB |
| `os` | string | p. ej. `Ubuntu 24.04` |
| `status` | `running` \| `stopped` \| `paused` \| `error` | Por defecto `stopped` |

## Tiempo real (WebSocket)

`/ws` envía a todos los usuarios conectados cada cambio que hace un Administrador:

```json
{"type": "vm.updated", "id": 6, "vm": {"id": 6, "name": "worker-01", "status": "running", "...": "..."}, "actor": "admin@vmdashboard.com", "at": "2026-10-05T10:14:31Z"}
```

`type` puede ser `vm.created`, `vm.updated` o `vm.deleted` (en este último `vm` es `null`).

- Autenticación con la misma cookie HttpOnly: el navegador la envía sola al abrir el socket. Sin cookie válida se rechaza la conexión.
- Se comprueba la cabecera `Origin` (los WebSockets no pasan por CORS) para que otra web no pueda abrir el socket con la sesión del usuario.
- Si el JWT caduca, el servidor cierra el socket con código `4401`; el frontend debe volver al login.
- El cliente puede enviar `"ping"` y recibe `{"type": "pong"}` para mantener viva la conexión.

```ts
const ws = new WebSocket("ws://localhost:8000/ws");   // wss:// en producción
ws.onmessage = (e) => { const event = JSON.parse(e.data); /* actualizar el estado global */ };
```

## Cómo debe llamar el frontend

El navegador guarda y envía la cookie solo; el frontend **no** toca el token. Lo único necesario es pedir que las peticiones incluyan credenciales:

```ts
// fetch
fetch("http://localhost:8000/vms", { credentials: "include" });

// Angular: interceptor que añade withCredentials a todas las peticiones
export const credentialsInterceptor: HttpInterceptorFn = (req, next) =>
  next(req.clone({ withCredentials: true }));

// axios
axios.defaults.withCredentials = true;
```

- Al cargar la app, llama a `GET /me`: si responde 200 hay sesión (y sabes el rol); si responde 401, muestra el login.
- Ante cualquier 401 posterior (sesión expirada), redirige al login. Para salir, `POST /logout`.
- Oculta los botones de crear/editar/borrar al rol Cliente; el backend lo impide igualmente (403).
- `localhost:4200` → `localhost:8000` cuenta como el mismo sitio, así que `SameSite=Lax` funciona en desarrollo. El origen del frontend debe estar en `VMD_CORS_ORIGINS`.
- En producción usa HTTPS y sirve frontend y API bajo el mismo dominio (p. ej. `app.midominio.com` y `api.midominio.com`). Si estuvieran en dominios distintos, haría falta `VMD_COOKIE_SAMESITE=none`.

## Configuración (variables `VMD_*` o archivo `.env`)

| Variable | Default | Uso |
|---|---|---|
| `VMD_DATABASE_URL` | `sqlite:///./vm_dashboard.db` | Base de datos |
| `VMD_SEED_DEMO_DATA` | `true` | Crea el usuario Cliente de ejemplo y 10 VMs si la base está vacía |
| `VMD_CORS_ORIGINS` | `["http://localhost:4200", "http://localhost:5173", "http://localhost:3000"]` | Orígenes del frontend |
| `VMD_JWT_SECRET` | secreto de desarrollo | **Cámbialo en producción**; si no, el servidor avisa al arrancar |
| `VMD_ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Duración de la sesión (token y cookie) |
| `VMD_COOKIE_SECURE` | `true` | Cookie solo por HTTPS (los navegadores la aceptan en `http://localhost`) |
| `VMD_COOKIE_SAMESITE` | `lax` | `lax`, `strict` o `none` |
| `VMD_ADMIN_EMAIL` / `VMD_ADMIN_PASSWORD` | `admin@vmdashboard.com` / `admin123` | Admin inicial |
| `VMD_CLIENT_EMAIL` / `VMD_CLIENT_PASSWORD` | `cliente@vmdashboard.com` / `cliente123` | Cliente de ejemplo |

## Estructura

```
app/
  main.py          # create_app: middlewares (CORS + JWT), routers, arranque de BD y semilla
  config.py        # Settings
  db.py            # SQLAlchemy: tablas users y vms, sesión por petición
  models.py        # Esquemas Pydantic (User, Role, VM, VMCreate, VMUpdate...)
  security.py      # bcrypt, emisión/validación de JWT, cookie HttpOnly
  middleware.py    # JWTCookieMiddleware
  deps.py          # get_current_user, require_admin
  seed.py          # Usuarios y VMs iniciales
  realtime.py      # WebSocket /ws y difusión de eventos
  simulation.py    # Métricas simuladas para las gráficas
  routers/         # auth.py, vms.py, users.py
tests/             # test_auth.py, test_vms.py, test_realtime.py
```

## Ejecutar en la propia tablet Android (Termux)

1. Instala **Termux** desde F-Droid (https://f-droid.org/packages/com.termux/). La versión de Google Play está desactualizada.
2. Descarga `vm-dashboard-backend.zip` en la tablet (queda en *Descargas*).
3. Abre Termux y ejecuta:

   ```bash
   termux-setup-storage            # acepta el permiso de almacenamiento
   pkg install -y unzip
   cp ~/storage/downloads/vm-dashboard-backend.zip ~ && cd ~ && unzip -o vm-dashboard-backend.zip
   bash vm-dashboard/backend/run-termux.sh
   ```

   La primera vez compila `pydantic-core` y `bcrypt`, así que tarda bastante (deja la tablet enchufada y la pantalla encendida). Las siguientes veces arranca en segundos con el mismo comando.
4. Con Termux abierto, ve a Chrome en la tablet y abre `http://localhost:8000/docs`. Haz `POST /login` con un usuario de ejemplo y luego `GET /vms`.

Al ser `localhost`, la cookie `Secure` funciona sin cambiar nada.

## Probar desde una tablet o móvil Android con el backend en tu ordenador

Alternativa sin instalar nada en la tablet: el backend corre en tu ordenador y la tablet lo abre por la Wi‑Fi.

1. Conecta el ordenador y la tablet a la misma red Wi‑Fi.
2. Averigua la IP local del ordenador (`ipconfig` en Windows, `ip addr` o `ifconfig` en Linux/macOS), p. ej. `192.168.1.50`.
3. Arranca el backend escuchando en la red y sin exigir HTTPS en la cookie:

   ```bash
   # Linux / macOS
   VMD_COOKIE_SECURE=false uvicorn app.main:app --host 0.0.0.0 --port 8000
   # Windows (PowerShell)
   $env:VMD_COOKIE_SECURE="false"; uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

4. En Chrome de la tablet abre `http://192.168.1.50:8000/docs`, ejecuta `POST /login` con un usuario de ejemplo y luego `GET /vms`.
5. Si no carga, permite Python o el puerto 8000 en el firewall del ordenador.

> `VMD_COOKIE_SECURE=false` es solo para esta prueba en red local: una cookie `Secure` solo viaja por HTTPS o `localhost`, y la IP de tu ordenador no es ninguna de las dos. En producción déjalo en `true` y usa HTTPS.
