"""ServicioAcciones (L4) — RF08, RF11, RF14, CU07 (secuencias secuencia_cu07_l4_orden / _ejecucion)."""
from datetime import datetime

from app.aplicacion.bitacora_auditoria import BitacoraAuditoria
from app.aplicacion.errores import DatosInvalidos, NoEncontrado, PermisoDenegado
from app.aplicacion.servicio_autenticacion import ServicioAutenticacion
from app.aplicacion.servicio_enrolamiento import ServicioEnrolamiento
from app.dominio.acciones import (
    Comando, ComandoFormateo, ComandoReinicioApagado, OrdenComando, ResultadoEjecucion, TransicionInvalida)
from app.dominio.base import ahora, nuevo_id
from app.dominio.enumeraciones import EstadoComando, ModoApagado, Permiso, TipoAccion
from app.dominio.monitoreo import Equipo
from app.dominio.repositorios import ComandoRepository, EquipoRepository
from app.dominio.usuarios import Sesion

# Acciones con ejecutor en el L5. El resto del catálogo del ERS (RF09, RF10, RF12) queda para el L6.
TIPOS_DISPONIBLES = (TipoAccion.REINICIAR_APAGAR, TipoAccion.FORMATEAR)


class ServicioAcciones:
    def __init__(self, comandos: ComandoRepository, equipos: EquipoRepository,
                 enrolamiento: ServicioEnrolamiento, autenticacion: ServicioAutenticacion,
                 bitacora: BitacoraAuditoria):
        self.comandos = comandos
        self.equipos = equipos
        self.enrolamiento = enrolamiento
        self.autenticacion = autenticacion
        self.bitacora = bitacora

    # ---- desde el panel ----------------------------------------------------------
    def crear_comando(self, s: Sesion, id_equipo: str, t: TipoAccion, p: dict[str, str]) -> Comando:
        equipo = self._equipo(id_equipo)
        try:
            self.autenticacion.autorizar(s, t.permiso_requerido())
        except PermisoDenegado:
            # Excepción 1f de CU07: el intento queda en la bitácora y la API responde 403.
            self.bitacora.registrar_intento_denegado(s.usuario, equipo, t)
            raise PermisoDenegado("Su rol no permite ordenar esta acción.", conservar_cambios=True)

        comando = self._construir(t, p, equipo)
        comando.id_comando = nuevo_id()
        comando.fecha_orden = ahora()
        comando.estado = EstadoComando.PENDIENTE
        comando.equipo = equipo
        comando.usuario = s.usuario
        # D11: primero la bitácora; si su escritura falla, la transacción completa se revierte
        # y la orden no llega a existir (RNF12).
        self.bitacora.registrar_orden(comando, s.usuario)
        self.comandos.guardar(comando)
        return comando

    def cancelar(self, s: Sesion, id_comando: str) -> Comando:
        self.autenticacion.autorizar(s, Permiso.ORDENAR_ACCION)
        comando = self._comando(id_comando)
        self.autenticacion.autorizar(s, comando.tipo().permiso_requerido())
        self._transicion(comando.cancelar)
        self.comandos.guardar(comando)
        self.bitacora.cerrar_entrada(comando, EstadoComando.CANCELADO)
        return comando

    def listar(self, s: Sesion, id_equipo: str | None, estado: EstadoComando | None, limite: int = 100) -> list[Comando]:
        self.autenticacion.autorizar(s, Permiso.CONSULTAR_PARQUE)
        equipo = self._equipo(id_equipo) if id_equipo else None
        return self.comandos.listar(equipo, estado, limite)

    # ---- desde el agente ---------------------------------------------------------
    def comandos_pendientes(self, token: str | None) -> list[OrdenComando]:
        equipo = self.enrolamiento.autenticar_agente(token)
        ordenes = []
        for comando in self.comandos.pendientes_de(equipo):
            comando.marcar_entregado()
            self.comandos.guardar(comando)
            ordenes.append(comando.a_orden())
        return ordenes

    def registrar_resultado(self, token: str | None, id_comando: str, r: ResultadoEjecucion) -> Comando:
        equipo = self.enrolamiento.autenticar_agente(token)
        comando = self.comandos.obtener_por_id(id_comando)
        if comando is None or comando.equipo_id != equipo.id_equipo:
            raise NoEncontrado("La orden no existe para este equipo.")
        self._transicion(lambda: comando.registrar_resultado(r))
        self.comandos.guardar(comando)
        self.bitacora.cerrar_entrada(comando, comando.estado)
        return comando

    # ---- tarea periódica ---------------------------------------------------------
    def expirar_vencidos(self, momento: datetime | None = None) -> list[Comando]:
        momento = momento or ahora()
        expirados = []
        for comando in self.comandos.vigentes():
            if comando.ha_expirado(momento):
                comando.expirar(momento)
                self.comandos.guardar(comando)
                self.bitacora.cerrar_entrada(comando, EstadoComando.EXPIRADO)
                expirados.append(comando)
        return expirados

    # ---- auxiliares --------------------------------------------------------------
    @staticmethod
    def _construir(t: TipoAccion, p: dict[str, str], equipo: Equipo) -> Comando:
        if t is TipoAccion.REINICIAR_APAGAR:
            try:
                modo = ModoApagado(p.get("modo", ""))
            except ValueError:
                raise DatosInvalidos("Indique el modo: «Reiniciar» o «Apagar».") from None
            return ComandoReinicioApagado(modo=modo)
        if t is TipoAccion.FORMATEAR:
            comando = ComandoFormateo(nombre_confirmado=p.get("nombreConfirmado", ""))
            if not comando.confirmacion_valida(equipo):  # RF11: sin la segunda confirmación no hay orden
                raise DatosInvalidos("El nombre escrito no coincide con el del equipo.")
            return comando
        raise DatosInvalidos(f"La acción {t.value} no está disponible en esta versión del prototipo.")

    @staticmethod
    def _transicion(accion) -> None:
        try:
            accion()
        except TransicionInvalida as error:
            raise DatosInvalidos(str(error)) from error

    def _equipo(self, id_equipo: str) -> Equipo:
        equipo = self.equipos.obtener_por_id(id_equipo)
        if equipo is None:
            raise NoEncontrado("El equipo no existe.")
        return equipo

    def _comando(self, id_comando: str) -> Comando:
        comando = self.comandos.obtener_por_id(id_comando)
        if comando is None:
            raise NoEncontrado("La orden no existe.")
        return comando
