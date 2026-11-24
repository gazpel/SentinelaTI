"""Ejecutores de acciones (L4, patrón Estrategia, decisión D12).

El agente elige el ejecutor cuyo ``soporta(tipo)`` es verdadero. Pasar una acción
de simulada a real significa cambiar un solo ejecutor.
"""
import logging
import platform
import subprocess
from abc import ABC, abstractmethod

from .modelo import OrdenComando, ResultadoEjecucion, TipoAccion

log = logging.getLogger("sentinela.agente")


class EjecutorAccion(ABC):
    simulado: bool = False

    @abstractmethod
    def soporta(self, t: TipoAccion) -> bool: ...

    @abstractmethod
    def ejecutar(self, o: OrdenComando) -> ResultadoEjecucion: ...


class EjecutorReinicioApagado(EjecutorAccion):
    """RF08. Usa ``shutdown.exe`` de Windows. Con ``acciones_reales=False`` (valor por defecto fuera
    de la VM de pruebas) solo registra lo que habría hecho: así se puede probar el flujo completo
    en el equipo de desarrollo sin apagarlo."""

    def __init__(self, acciones_reales: bool, ejecutar_proceso=subprocess.run):
        self.acciones_reales = acciones_reales
        self._ejecutar_proceso = ejecutar_proceso

    def soporta(self, t: TipoAccion) -> bool:
        return t is TipoAccion.REINICIAR_APAGAR

    def ejecutar(self, o: OrdenComando) -> ResultadoEjecucion:
        modo = o.parametros.get("modo")
        if modo not in ("Reiniciar", "Apagar"):
            return ResultadoEjecucion(False, f"Modo desconocido: {modo!r}")
        argumentos = ["shutdown", "/r" if modo == "Reiniciar" else "/s", "/t", "15",
                      "/c", "SentinelaTI: acción ordenada por el área de TI."]
        if not self.acciones_reales:
            log.warning("[modo seguro] Se habría ejecutado: %s", " ".join(argumentos))
            return ResultadoEjecucion(True, "Modo seguro: la orden no se ejecutó en el equipo real.")
        if platform.system() != "Windows":
            return ResultadoEjecucion(False, "El reinicio remoto solo está soportado en Windows (RNF09).")
        r = self._ejecutar_proceso(argumentos, capture_output=True, text=True)
        if r.returncode != 0:
            return ResultadoEjecucion(False, (r.stderr or r.stdout or f"código {r.returncode}").strip())
        return ResultadoEjecucion(True, None)


class EjecutorSimulado(EjecutorAccion):
    """RF10–RF12 (y el formateo de RF11 en el L5): recorre el ciclo de vida sin tocar el equipo."""

    simulado = True
    TIPOS = (TipoAccion.FORMATEAR, TipoAccion.ACTUALIZAR_SO, TipoAccion.ESCRITORIO_REMOTO)

    def soporta(self, t: TipoAccion) -> bool:
        return t in self.TIPOS

    def ejecutar(self, o: OrdenComando) -> ResultadoEjecucion:
        log.info("[simulado] %s %s", o.tipo.value, o.parametros or "")
        return ResultadoEjecucion(True, "Ejecución simulada (prototipo).")
