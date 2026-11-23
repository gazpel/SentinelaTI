"""Configuración de la API, leída de variables de entorno (ver backend/.env.example)."""
import os
from dataclasses import dataclass, field


def _bool(nombre: str, defecto: bool) -> bool:
    return os.getenv(nombre, str(defecto)).strip().lower() in ("1", "true", "si", "sí", "yes")


@dataclass
class Configuracion:
    # SQLite para desarrollo; en producción: postgresql+psycopg://usuario:clave@host/sentinela (RNF10).
    url_bd: str = field(default_factory=lambda: os.getenv("SENTINELA_BD_URL", "sqlite:///./sentinela.sqlite3"))
    secreto_jwt: str = field(default_factory=lambda: os.getenv("SENTINELA_SECRETO_JWT", "solo-desarrollo-cambiar-en-produccion"))
    horas_sesion: int = field(default_factory=lambda: int(os.getenv("SENTINELA_HORAS_SESION", "8")))  # CU03
    codigo_enrolamiento: str = field(default_factory=lambda: os.getenv("SENTINELA_CODIGO_ENROLAMIENTO", "SENTINELA-DEMO-2026"))
    intervalo_reporte_min: int = field(default_factory=lambda: int(os.getenv("SENTINELA_INTERVALO_REPORTE_MIN", "5")))  # RF02
    tareas_periodicas: bool = field(default_factory=lambda: _bool("SENTINELA_TAREAS_PERIODICAS", True))
    segundos_tareas: int = 60
    # Administrador inicial: se crea solo si la base no tiene usuarios.
    correo_admin: str = field(default_factory=lambda: os.getenv("SENTINELA_ADMIN_CORREO", "admin@sentinela.local"))
    clave_admin: str = field(default_factory=lambda: os.getenv("SENTINELA_ADMIN_CLAVE", "Admin.2026"))
    origenes_cors: list[str] = field(default_factory=lambda: os.getenv(
        "SENTINELA_ORIGENES_CORS", "http://localhost:5173,http://127.0.0.1:5173").split(","))
