"""AgenteSentinela (L4) — coordina recolección, envío con cola local y ejecución de órdenes.

Secuencias que implementa: secuencia_cu02_l4_recepcion (ciclo_reporte),
secuencia_cu02_l4_sin_conexion (cola local) y secuencia_cu07_l4_ejecucion
(ciclo_comandos → seleccionar_ejecutor → ejecutar_comando).
"""
import logging
import threading
import time

from .almacen_token import AlmacenToken
from .cliente_api import ClienteAPI, ErrorRed, ErrorServidor, TokenRechazado
from .cola_local import ColaLocalLecturas
from .config import ConfiguracionAgente
from .ejecutores import EjecutorAccion, EjecutorReinicioApagado, EjecutorSimulado
from .modelo import OrdenComando, ResultadoEjecucion, TipoAccion
from .notificador import NotificadorUsuario
from .recolectores import RecolectorInventario, RecolectorMetricas

log = logging.getLogger("sentinela.agente")


class SinEjecutor(Exception):
    pass


class AgenteSentinela:
    def __init__(self, cfg: ConfiguracionAgente, cliente: ClienteAPI | None = None,
                 recolector: RecolectorMetricas | None = None, inventario: RecolectorInventario | None = None,
                 cola: ColaLocalLecturas | None = None, notificador: NotificadorUsuario | None = None,
                 almacen: AlmacenToken | None = None, ejecutores: list[EjecutorAccion] | None = None):
        cfg.carpeta_datos.mkdir(parents=True, exist_ok=True)
        self.cfg = cfg
        self.almacen = almacen or AlmacenToken(cfg.carpeta_datos)
        self.cliente = cliente or ClienteAPI(cfg.url_servidor, self.almacen.leer())
        self.recolector = recolector or RecolectorMetricas()
        self.inventario = inventario or RecolectorInventario()
        self.cola = cola or ColaLocalLecturas(cfg.carpeta_datos / "cola_local.sqlite3")
        self.notificador = notificador or NotificadorUsuario(cfg.segundos_aviso)
        self.ejecutores = ejecutores or [EjecutorReinicioApagado(cfg.acciones_reales), EjecutorSimulado()]
        self.intervalo_reporte_seg = cfg.intervalo_reporte_min * 60
        self._detener = threading.Event()

    # ---- arranque y enrolamiento (CU01) ---------------------------------------
    def iniciar(self) -> None:
        self.notificador.mostrar_icono_bandeja()
        if not self.cliente.token:
            self.enrolar(self.cfg.codigo_enrolamiento)
        proximo_reporte = proximo_sondeo = 0.0
        while not self._detener.is_set():
            ahora = time.monotonic()
            if ahora >= proximo_reporte:
                self.ciclo_reporte()
                proximo_reporte = ahora + self.intervalo_reporte_seg
            if ahora >= proximo_sondeo:
                self.ciclo_comandos()
                proximo_sondeo = ahora + self.cfg.intervalo_comandos_seg
            self._detener.wait(1)

    def detener(self) -> None:
        self._detener.set()

    def enrolar(self, codigo: str) -> bool:
        if not codigo:
            raise SystemExit("Falta el código de enrolamiento (--codigo o SENTINELA_CODIGO_ENROLAMIENTO).")
        datos = self.inventario.leer_hardware()
        token, intervalo_servidor = self.cliente.post_enrolamiento(codigo, datos)
        self.almacen.guardar(token)
        self.intervalo_reporte_seg = intervalo_servidor * 60
        log.info("Equipo %s enrolado. Reporta cada %d min.", datos.nombre, intervalo_servidor)
        return True

    # ---- reporte de métricas (CU02, RF02, RNF04) -------------------------------
    def ciclo_reporte(self) -> None:
        lectura = self.recolector.componer_lectura()
        # Primero se vacía la cola, para que el servidor reciba las lecturas en orden cronológico.
        if self._reenviar_pendientes():
            try:
                self.cliente.post_lectura(lectura)
                log.info("Lectura enviada: CPU %.0f%% · RAM %.0f%%", lectura.uso_cpu, lectura.uso_ram)
                return
            except ErrorRed:
                log.warning("Sin conexión con el servidor: la lectura queda en la cola local.")
            except TokenRechazado:
                self._reenrolar()
        self.cola.encolar(lectura)

    def _reenviar_pendientes(self) -> bool:
        """Devuelve True si la cola quedó vacía."""
        for pendiente in self.cola.pendientes():
            try:
                self.cliente.post_lectura(pendiente)
            except (ErrorRed, TokenRechazado):
                return False
            except ErrorServidor as error:  # lectura rechazada por inválida: no se reintenta para siempre
                log.error("Lectura descartada por el servidor: %s", error)
            self.cola.confirmar_envio(pendiente)
        return True

    def _reenrolar(self) -> None:
        log.warning("El servidor rechazó el token: se intenta enrolar de nuevo (CU02, 3a).")
        self.almacen.borrar()
        self.cliente.token = None
        if self.cfg.codigo_enrolamiento:
            try:
                self.enrolar(self.cfg.codigo_enrolamiento)
            except Exception as error:  # el código pudo cambiar: se sigue encolando
                log.error("No se pudo reenrolar: %s", error)

    # ---- órdenes remotas (CU07, RF08) -------------------------------------------
    def ciclo_comandos(self) -> list[threading.Thread]:
        try:
            ordenes = self.cliente.get_comandos_pendientes()
        except (ErrorRed, TokenRechazado, ErrorServidor) as error:
            log.debug("No se pudieron consultar órdenes: %s", error)
            return []
        hilos = []
        for orden in ordenes:
            # Cada orden corre en su hilo: el aviso de 5 minutos no detiene el envío de lecturas.
            hilo = threading.Thread(target=self.ejecutar_comando, args=(orden,), daemon=True)
            hilo.start()
            hilos.append(hilo)
        return hilos

    def seleccionar_ejecutor(self, t: TipoAccion) -> EjecutorAccion:
        for ejecutor in self.ejecutores:
            if ejecutor.soporta(t):
                return ejecutor
        raise SinEjecutor(f"No hay ejecutor para {t.value}")

    def ejecutar_comando(self, o: OrdenComando) -> ResultadoEjecucion:
        log.info("Orden recibida: %s %s", o.tipo.value, o.parametros)
        try:
            ejecutor = self.seleccionar_ejecutor(o.tipo)
            if o.interrumpe_uso:  # <<include>> CU08 (RF15)
                self.notificador.mostrar_aviso(o)
            resultado = ejecutor.ejecutar(o)
        except Exception as error:
            resultado = ResultadoEjecucion(False, str(error))
        try:
            self.cliente.post_resultado(o.id_comando, resultado)
        except (ErrorRed, ErrorServidor, TokenRechazado) as error:
            log.error("No se pudo informar el resultado de %s: %s", o.id_comando, error)
        return resultado
