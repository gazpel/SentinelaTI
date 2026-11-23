"""NotificadorUsuario (L4) — RF15, RNF11 (wireframe W3).

En el L5 el aviso es una versión de consola: registra la acción y espera la
cuenta regresiva configurada. La ventana con «Posponer 30 minutos» y el ícono
de la bandeja del sistema (W3) quedan para el L6.
"""
import logging
import time

from .modelo import DesenlaceAviso, OrdenComando

log = logging.getLogger("sentinela.agente")

TEXTOS = {"Reiniciar": "Su equipo se reiniciará", "Apagar": "Su equipo se apagará"}


class NotificadorUsuario:
    def __init__(self, segundos_aviso: int, esperar=time.sleep):
        self.segundos_aviso = segundos_aviso
        self._esperar = esperar

    def mostrar_aviso(self, o: OrdenComando) -> DesenlaceAviso:
        titulo = TEXTOS.get(o.parametros.get("modo", ""), f"El área de TI ejecutará: {o.tipo.value}")
        log.warning("AVISO AL USUARIO: %s en %d s. Guarde su trabajo.", titulo, self.segundos_aviso)
        if self.segundos_aviso > 0:
            self._esperar(self.segundos_aviso)
        return DesenlaceAviso.CUENTA_TERMINADA

    def mostrar_icono_bandeja(self) -> None:
        log.info("SentinelaTI activo: recolecta CPU, RAM, disco, temperatura y horas encendido (RNF05, RNF11).")
