"""RecolectorMetricas y RecolectorInventario (L4) — RF02 y datos de enrolamiento (D4, RNF05).

Solo se leen contadores del sistema: nunca archivos, correos, navegación,
teclado ni pantalla.
"""
import platform
import socket
import subprocess
import time
from datetime import datetime, timezone

import psutil

from .modelo import DatosEquipo, Lectura, UsoDisco


class RecolectorMetricas:
    def __init__(self):
        psutil.cpu_percent(interval=None)  # la primera medición de psutil siempre es 0: se descarta

    def componer_lectura(self) -> Lectura:
        return Lectura(
            marca_tiempo=datetime.now(timezone.utc),
            uso_cpu=psutil.cpu_percent(interval=1),
            uso_ram=psutil.virtual_memory().percent,
            discos=self._discos(),
            temperatura_cpu=self._temperatura(),
            horas_encendido=(time.time() - psutil.boot_time()) / 3600,
        )

    @staticmethod
    def _discos() -> list[UsoDisco]:
        discos = []
        for particion in psutil.disk_partitions(all=False):
            if "cdrom" in particion.opts or not particion.fstype:
                continue
            try:
                uso = psutil.disk_usage(particion.mountpoint)
            except OSError:  # unidad sin medio o sin permiso
                continue
            discos.append(UsoDisco(particion.device.rstrip("\\"), uso.percent))
        return discos or [UsoDisco("?", 0.0)]

    @staticmethod
    def _temperatura() -> float | None:
        """Riesgo R1 del L1: Windows no expone la temperatura de forma estándar. Se intenta la zona
        térmica ACPI por WMI; si no existe (lo usual en VMs), queda «no disponible» (RF02)."""
        lector = getattr(psutil, "sensors_temperatures", None)
        if lector:
            for sensores in (lector() or {}).values():
                if sensores:
                    return sensores[0].current
        if platform.system() == "Windows":
            salida = _powershell("(Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature "
                                 "-ErrorAction Stop | Select-Object -First 1).CurrentTemperature")
            if salida and salida.isdigit():
                return int(salida) / 10 - 273.15  # décimas de kelvin → °C
        return None


class RecolectorInventario:
    """En el L5 solo lee lo necesario para el enrolamiento; el inventario completo (RF03) queda para el L6."""

    def leer_hardware(self) -> DatosEquipo:
        return DatosEquipo(
            nombre=socket.gethostname(),
            numero_serie=self._numero_serie(),
            modelo=_powershell("(Get-CimInstance Win32_ComputerSystem).Model") or platform.machine(),
            sistema_operativo=f"{platform.system()} {platform.release()} ({platform.version()})",
            direccion_ip=self._ip_local(),
            ultimo_usuario=self._ultimo_usuario(),
        )

    @staticmethod
    def _numero_serie() -> str:
        """El número de serie identifica al equipo en el servidor (un reenrolamiento con la misma serie
        reutiliza el registro). Muchas placas y VMs traen un valor genérico de fábrica: si se usara tal
        cual, equipos distintos se fusionarían en uno solo. En ese caso se usa el UUID del sistema."""
        serie = _powershell("(Get-CimInstance Win32_BIOS).SerialNumber")
        if es_serie_valida(serie):
            return serie
        uuid = _powershell("(Get-CimInstance Win32_ComputerSystemProduct).UUID")
        if es_serie_valida(uuid):
            return f"UUID-{uuid}"
        return f"SIN-SERIE-{socket.gethostname()}"


SERIES_GENERICAS = {
    "", "0", "none", "n/a", "na", "default string", "to be filled by o.e.m.", "system serial number",
    "not specified", "not applicable", "chassis serial number", "serial number", "123456789", "0123456789",
    "00000000-0000-0000-0000-000000000000", "ffffffff-ffff-ffff-ffff-ffffffffffff",
    "03000200-0400-0500-0006-000700080009",
}


def es_serie_valida(serie: str | None) -> bool:
    return bool(serie) and serie.strip().lower() not in SERIES_GENERICAS

    @staticmethod
    def _ip_local() -> str | None:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("10.255.255.255", 1))  # no envía paquetes: solo elige la interfaz de salida
                return s.getsockname()[0]
        except OSError:
            return None

    @staticmethod
    def _ultimo_usuario() -> str | None:
        usuarios = psutil.users()
        return usuarios[-1].name if usuarios else None


def _powershell(comando: str) -> str | None:
    if platform.system() != "Windows":
        return None
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", comando],
                           capture_output=True, text=True, timeout=15)
        return r.stdout.strip() or None if r.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None
