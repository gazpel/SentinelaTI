"""GestorAlertas (L4) — RF16: como máximo una alerta abierta por equipo y métrica."""
from app.aplicacion.servicio_autenticacion import ServicioAutenticacion
from app.dominio.base import ahora
from app.dominio.enumeraciones import Metrica, NivelAlerta, Permiso
from app.dominio.monitoreo import Alerta, ConfiguracionUmbrales, Equipo, Lectura, Umbral
from app.dominio.repositorios import AlertaRepository
from app.dominio.usuarios import Sesion


class GestorAlertas:
    def __init__(self, alertas: AlertaRepository, autenticacion: ServicioAutenticacion | None = None):
        self.alertas = alertas
        self.autenticacion = autenticacion

    def evaluar(self, e: Equipo, l: Lectura, configuracion: ConfiguracionUmbrales) -> list[Alerta]:
        """Abre una alerta por cada métrica que supera su umbral crítico y cierra las que volvieron
        bajo el umbral. Una lectura nueva también cierra la alerta de desconexión."""
        cambios: list[Alerta] = []
        for metrica in Metrica:
            nivel = self.evaluar_metrica(l, metrica, configuracion.umbral_de(metrica))
            abierta = self.alertas.abierta_de(e, metrica)
            if nivel is NivelAlerta.CRITICO and abierta is None:
                nueva = Alerta(equipo_id=e.id_equipo, metrica=metrica, nivel=NivelAlerta.CRITICO,
                               valor=l.valor_de(metrica), fecha_apertura=l.marca_tiempo)
                self.alertas.guardar(nueva)
                cambios.append(nueva)
            elif nivel is not NivelAlerta.CRITICO and abierta is not None:
                self.cerrar_alerta(abierta)
                cambios.append(abierta)
        desconexion = self.alertas.abierta_de(e, None)
        if desconexion is not None:
            self.cerrar_alerta(desconexion)
            cambios.append(desconexion)
        return cambios

    @staticmethod
    def evaluar_metrica(l: Lectura, m: Metrica, u: Umbral) -> NivelAlerta:
        return u.evaluar(l.valor_de(m))

    def registrar_desconexion(self, e: Equipo) -> Alerta:
        abierta = self.alertas.abierta_de(e, None)
        if abierta is not None:
            return abierta
        alerta = Alerta(equipo_id=e.id_equipo, metrica=None, nivel=NivelAlerta.CRITICO, fecha_apertura=ahora())
        self.alertas.guardar(alerta)
        return alerta

    def cerrar_alerta(self, a: Alerta) -> None:
        a.cerrar()
        self.alertas.guardar(a)

    def consultar_abiertas(self, s: Sesion, pagina: int, tamano: int) -> tuple[list[Alerta], int]:
        self.autenticacion.autorizar(s, Permiso.CONSULTAR_PARQUE)
        return self.alertas.listar_abiertas(pagina, tamano)

    def contar_abiertas(self, s: Sesion) -> int:
        self.autenticacion.autorizar(s, Permiso.CONSULTAR_PARQUE)
        return self.alertas.contar_abiertas()
