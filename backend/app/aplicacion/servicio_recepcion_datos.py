"""ServicioRecepcionDatos (L4, cambio C1) — RF02, CU02 (secuencia_cu02_l4_recepcion)."""
from app.aplicacion.gestor_alertas import GestorAlertas
from app.aplicacion.servicio_enrolamiento import ServicioEnrolamiento
from app.dominio.monitoreo import Lectura
from app.dominio.repositorios import ConfiguracionRepository, EquipoRepository, LecturaRepository


class ServicioRecepcionDatos:
    def __init__(self, enrolamiento: ServicioEnrolamiento, equipos: EquipoRepository,
                 lecturas: LecturaRepository, gestor_alertas: GestorAlertas,
                 configuracion: ConfiguracionRepository):
        self.enrolamiento = enrolamiento
        self.equipos = equipos
        self.lecturas = lecturas
        self.gestor_alertas = gestor_alertas
        self.configuracion = configuracion

    def recibir_lectura(self, token: str | None, l: Lectura) -> bool:
        """Registra la lectura. Devuelve False si ya existía (reenvío desde la cola local, RNF04):
        la petición se responde igual con éxito para que el agente la saque de su cola."""
        equipo = self.enrolamiento.autenticar_agente(token)
        if self.lecturas.existe(equipo, l.marca_tiempo):
            return False
        era_la_mas_reciente = equipo.fecha_ultimo_reporte is None or l.marca_tiempo >= equipo.fecha_ultimo_reporte
        equipo.registrar_lectura(l)
        self.lecturas.agregar(equipo, l)
        # Una lectura atrasada (llega desde la cola) se guarda para el historial,
        # pero no cambia el estado ni las alertas, que reflejan la situación actual.
        if era_la_mas_reciente:
            configuracion = self.configuracion.obtener()
            self.gestor_alertas.evaluar(equipo, l, configuracion)
            equipo.evaluar_estado(configuracion)
        self.equipos.guardar(equipo)
        return True
