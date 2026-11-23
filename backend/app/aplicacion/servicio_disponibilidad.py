"""ServicioDisponibilidad (L4, cambio C1) — estado Desconectado (RF05, RF16; secuencia_cu02_l4_disponibilidad)."""
from datetime import datetime, timedelta

from app.aplicacion.gestor_alertas import GestorAlertas
from app.dominio.base import ahora
from app.dominio.monitoreo import Equipo
from app.dominio.repositorios import EquipoRepository


class ServicioDisponibilidad:
    intervalos_tolerados = 3

    def __init__(self, equipos: EquipoRepository, gestor_alertas: GestorAlertas, intervalo_reporte_min: int):
        self.equipos = equipos
        self.gestor_alertas = gestor_alertas
        self.intervalo_reporte = timedelta(minutes=intervalo_reporte_min)

    def detectar_desconectados(self, momento: datetime | None = None) -> list[Equipo]:
        limite = (momento or ahora()) - self.intervalos_tolerados * self.intervalo_reporte
        marcados = self.equipos.listar_sin_reporte_desde(limite)
        for equipo in marcados:
            equipo.marcar_desconectado()
            self.equipos.guardar(equipo)
            self.gestor_alertas.registrar_desconexion(equipo)
        return marcados
