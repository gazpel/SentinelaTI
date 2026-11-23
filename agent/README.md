# SentinelaTI — Agente para Windows 10/11

Recolecta CPU, RAM, discos, temperatura y horas encendido (RF02), las envía a la API con una cola local
para cuando no hay red (RNF04) y ejecuta las órdenes remotas que consulta cada 60 s (RF08).

| Módulo | Clase del L4 |
|---|---|
| `agente.py` | `AgenteSentinela` |
| `recolectores.py` | `RecolectorMetricas`, `RecolectorInventario` |
| `cola_local.py` | `ColaLocalLecturas` (SQLite) |
| `cliente_api.py` | `ClienteAPI` |
| `ejecutores.py` | `EjecutorAccion`, `EjecutorReinicioApagado`, `EjecutorSimulado` (patrón Estrategia) |
| `notificador.py` | `NotificadorUsuario` (aviso en consola en el L5) |
| `almacen_token.py` | `AlmacenToken` |

## Ejecutar

Con la API corriendo (ver `backend/README.md`), desde `agent/`:

```powershell
..\.venv\Scripts\python -m sentinela_agente --servidor http://localhost:8000 --codigo SENTINELA-DEMO-2026
```

Opciones útiles: `--una-vez` (una lectura y una consulta de órdenes), `--intervalo 1` (minutos entre lecturas, 1–60),
`--aviso 10` (segundos de cuenta regresiva antes de reiniciar), `--datos <carpeta>` (token y cola local;
por defecto `%PROGRAMDATA%\SentinelaTI`).

### Modo seguro

Por defecto el agente **no** reinicia ni apaga el equipo: registra el comando que habría ejecutado e informa el
resultado. Para que la acción sea real, **solo en la VM de pruebas**:

```powershell
$env:SENTINELA_ACCIONES_REALES = "1"
```

## Pruebas

```powershell
..\.venv\Scripts\python -m pytest
```

19 pruebas; la API se simula con `httpx.MockTransport`, así que no hace falta el servidor.

## Pendiente (L6)

Instalación como servicio de Windows (RNF02), token protegido con DPAPI, ventana de aviso con «Posponer 30 minutos»
e ícono de bandeja (RF15, RNF11), inventario de aplicaciones (RF03) y actualizaciones pendientes (RF04).
