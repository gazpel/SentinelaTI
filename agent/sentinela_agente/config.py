"""Configuración del agente (variables de entorno o argumentos de la línea de comandos)."""
import os
from dataclasses import dataclass, field
from pathlib import Path

INTERVALO_MIN = 1    # RF02: intervalo configurable entre 1 y 60 minutos
INTERVALO_MAX = 60


class ConfiguracionInvalida(ValueError):
    pass


def validar_intervalo_reporte(minutos: int) -> int:
    """Entrada con particiones de equivalencia en el plan de pruebas: <1 | 1..60 | >60."""
    if isinstance(minutos, bool) or not isinstance(minutos, int):
        raise ConfiguracionInvalida("El intervalo de reporte debe ser un número entero de minutos.")
    if not (INTERVALO_MIN <= minutos <= INTERVALO_MAX):
        raise ConfiguracionInvalida(
            f"El intervalo de reporte debe estar entre {INTERVALO_MIN} y {INTERVALO_MAX} minutos (RF02).")
    return minutos


@dataclass
class ConfiguracionAgente:
    url_servidor: str = field(default_factory=lambda: os.getenv("SENTINELA_SERVIDOR", "http://localhost:8000"))
    codigo_enrolamiento: str = field(default_factory=lambda: os.getenv("SENTINELA_CODIGO_ENROLAMIENTO", ""))
    intervalo_reporte_min: int = 5
    # Si el intervalo se configuró explícitamente en el equipo, prevalece sobre el que sugiere el servidor.
    intervalo_explicito: bool = False
    intervalo_comandos_seg: int = 60  # sondeo de órdenes (D2)
    carpeta_datos: Path = field(default_factory=lambda: Path(os.getenv(
        "SENTINELA_DATOS", Path(os.getenv("PROGRAMDATA", Path.home())) / "SentinelaTI")))
    # Salvaguarda del prototipo: el reinicio/apagado real solo ocurre si se activa
    # explícitamente (en la VM de pruebas). Si no, se registra como ejecutado sin tocar el equipo.
    acciones_reales: bool = field(default_factory=lambda: os.getenv("SENTINELA_ACCIONES_REALES", "0") == "1")
    segundos_aviso: int = 300  # RF15: cuenta regresiva de 5 minutos

    def __post_init__(self):
        validar_intervalo_reporte(self.intervalo_reporte_min)
        self.carpeta_datos = Path(self.carpeta_datos)
