# SentinelaTI — API (backend)

API REST en FastAPI con las cuatro capas del diseño del L4:

| Paquete | Capa | Contenido |
|---|---|---|
| `app/presentacion` | Presentación | Routers del panel (`/api/panel`, JWT) y del agente (`/api/agente`, token), esquemas JSON, tareas periódicas |
| `app/aplicacion` | Aplicación | Un servicio por archivo (`ServicioAcciones`, `GestorAlertas`, …) |
| `app/dominio` | Dominio | Entidades, enumeraciones y contratos `*Repository` |
| `app/infraestructura` | Infraestructura | Conexión a la base de datos, `*RepositorySql`, hash de contraseñas y JWT |

## Ejecutar

Desde la raíz del repositorio (una sola vez):

```powershell
python -m venv .venv
.venv\Scripts\pip install -r backend/requirements.txt -r agent/requirements.txt -r requirements-dev.txt
```

Desde `backend/`:

```powershell
..\.venv\Scripts\python -m scripts.sembrar_demo --reiniciar   # opcional: 20 equipos ficticios con 30 días de historial
..\.venv\Scripts\python -m uvicorn app.main:app --port 8000
```

El contrato OpenAPI queda en <http://localhost:8000/docs>.

### Usuarios de prueba (solo desarrollo)

| Rol | Correo | Contraseña |
|---|---|---|
| Administrador | `admin@sentinela.local` | `Admin.2026` (se crea al iniciar si no hay usuarios) |
| Técnico | `tecnico@sentinela.local` | `Tecnico.2026` (lo crea `sembrar_demo`) |

Código de enrolamiento de los agentes: `SENTINELA-DEMO-2026`.

### Variables de entorno

| Variable | Por defecto | Uso |
|---|---|---|
| `SENTINELA_BD_URL` | `sqlite:///./sentinela.sqlite3` | En producción: `postgresql+psycopg://usuario:clave@host/sentinela` (instalar `psycopg[binary]`) |
| `SENTINELA_SECRETO_JWT` | valor de desarrollo | **Cambiar** fuera de desarrollo (≥ 32 caracteres) |
| `SENTINELA_CODIGO_ENROLAMIENTO` | `SENTINELA-DEMO-2026` | Código que presentan los agentes (RF01) |
| `SENTINELA_ADMIN_CORREO` / `SENTINELA_ADMIN_CLAVE` | ver tabla anterior | Administrador inicial |
| `SENTINELA_INTERVALO_REPORTE_MIN` | `5` | Intervalo de reporte esperado; 3 intervalos sin reporte = Desconectado |
| `SENTINELA_TAREAS_PERIODICAS` | `1` | Detección de desconexión y expiración de órdenes cada 60 s |
| `SENTINELA_HORAS_SESION` | `8` | Duración de la sesión del panel (CU03) |

Para HTTPS (RNF01): `uvicorn app.main:app --ssl-keyfile clave.pem --ssl-certfile cert.pem`.

## Pruebas

```powershell
..\.venv\Scripts\python -m pytest
```

106 pruebas. Cada archivo agrupa los casos del plan de pruebas por requerimiento (`test_rf17_rf13_usuarios.py`, …); el nombre de cada prueba empieza con su ID (`test_cp04_…`). El detalle está en `docs/L5`.
