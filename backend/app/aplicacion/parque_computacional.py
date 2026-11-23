"""ParqueComputacional (L4, dominio «Monitoreo del parque») — RF05, RF06, CU04, CU05.

En el diseño es una clase del dominio que agrupa los equipos. Como el prototipo
administra un solo parque, aquí es un objeto sin estado propio que resuelve sus
consultas con los repositorios (decisión D6: filtros y orden en la base de datos).
"""
from datetime import timedelta

from app.aplicacion.errores import DatosInvalidos, NoEncontrado
from app.aplicacion.servicio_autenticacion import ServicioAutenticacion
from app.dominio.base import ahora
from app.dominio.enumeraciones import EstadoEquipo, Permiso
from app.dominio.monitoreo import Equipo, Lectura
from app.dominio.repositorios import AlertaRepository, EquipoRepository, LecturaRepository
from app.dominio.usuarios import Sesion

RANGOS_HISTORIAL = {"24h": timedelta(hours=24), "7d": timedelta(days=7), "30d": timedelta(days=30)}  # RF06
TAMANO_MAXIMO_PAGINA = 100


class ParqueComputacional:
    nombre = "Parque principal"

    def __init__(self, equipos: EquipoRepository, lecturas: LecturaRepository,
                 alertas: AlertaRepository, autenticacion: ServicioAutenticacion):
        self.equipos = equipos
        self.lecturas = lecturas
        self.alertas = alertas
        self.autenticacion = autenticacion

    def listar(self, s: Sesion, estado: EstadoEquipo | None, texto: str | None,
               pagina: int = 1, tamano: int = 25) -> tuple[list[Equipo], int]:
        """listar() y buscar() del diseño en una sola operación: los filtros se combinan (RF05)."""
        self.autenticacion.autorizar(s, Permiso.CONSULTAR_PARQUE)
        if pagina < 1 or not (1 <= tamano <= TAMANO_MAXIMO_PAGINA):
            raise DatosInvalidos(f"La página debe ser ≥ 1 y el tamaño entre 1 y {TAMANO_MAXIMO_PAGINA}.")
        return self.equipos.listar_con_filtros(estado, (texto or "").strip() or None, pagina, tamano)

    def resumen_por_estado(self, s: Sesion) -> dict[EstadoEquipo, int]:
        self.autenticacion.autorizar(s, Permiso.CONSULTAR_PARQUE)
        return self.equipos.contar_por_estado()

    def detalle(self, s: Sesion, id_equipo: str) -> tuple[Equipo, Lectura | None, list]:
        self.autenticacion.autorizar(s, Permiso.CONSULTAR_PARQUE)
        equipo = self._equipo(id_equipo)
        return equipo, self.lecturas.ultima(equipo), self.alertas.abiertas_de_equipo(equipo)

    def historial(self, s: Sesion, id_equipo: str, rango: str) -> list[Lectura]:
        self.autenticacion.autorizar(s, Permiso.CONSULTAR_PARQUE)
        if rango not in RANGOS_HISTORIAL:
            raise DatosInvalidos("El rango debe ser 24h, 7d o 30d.")
        equipo = self._equipo(id_equipo)
        hasta = ahora()
        return self.lecturas.historial(equipo, hasta - RANGOS_HISTORIAL[rango], hasta)

    def _equipo(self, id_equipo: str) -> Equipo:
        equipo = self.equipos.obtener_por_id(id_equipo)
        if equipo is None:
            raise NoEncontrado("El equipo no existe.")
        return equipo
