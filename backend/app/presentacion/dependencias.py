"""Composición de dependencias por petición.

Cada petición HTTP recibe una sesión de base de datos (una transacción) y un
Contenedor que arma los servicios con los repositorios SQL. Es el único lugar
donde la capa de aplicación se conecta con la infraestructura.
"""
from collections.abc import Iterator
from functools import cached_property

from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session

from app.aplicacion.bitacora_auditoria import BitacoraAuditoria
from app.aplicacion.errores import ErrorAplicacion
from app.aplicacion.gestor_alertas import GestorAlertas
from app.aplicacion.parque_computacional import ParqueComputacional
from app.aplicacion.servicio_acciones import ServicioAcciones
from app.aplicacion.servicio_autenticacion import ServicioAutenticacion
from app.aplicacion.servicio_configuracion import ServicioConfiguracion
from app.aplicacion.servicio_disponibilidad import ServicioDisponibilidad
from app.aplicacion.servicio_enrolamiento import ServicioEnrolamiento
from app.aplicacion.servicio_recepcion_datos import ServicioRecepcionDatos
from app.aplicacion.servicio_usuarios import ServicioUsuarios
from app.config import Configuracion
from app.dominio.usuarios import Sesion
from app.infraestructura import repositorios_sql as repos


class Contenedor:
    def __init__(self, bd: Session, cfg: Configuracion):
        self.bd = bd
        self.cfg = cfg

    # repositorios
    @cached_property
    def usuarios(self): return repos.UsuarioRepositorySql(self.bd)
    @cached_property
    def equipos(self): return repos.EquipoRepositorySql(self.bd)
    @cached_property
    def lecturas(self): return repos.LecturaRepositorySql(self.bd)
    @cached_property
    def alertas(self): return repos.AlertaRepositorySql(self.bd)
    @cached_property
    def configuracion(self): return repos.ConfiguracionRepositorySql(self.bd)
    @cached_property
    def comandos(self): return repos.ComandoRepositorySql(self.bd)
    @cached_property
    def registros_bitacora(self): return repos.BitacoraRepositorySql(self.bd)

    # servicios
    @cached_property
    def autenticacion(self):
        return ServicioAutenticacion(self.usuarios, self.cfg.secreto_jwt, self.cfg.horas_sesion)
    @cached_property
    def servicio_usuarios(self): return ServicioUsuarios(self.usuarios, self.autenticacion)
    @cached_property
    def servicio_configuracion(self): return ServicioConfiguracion(self.configuracion, self.autenticacion)
    @cached_property
    def enrolamiento(self): return ServicioEnrolamiento(self.equipos, self.cfg.codigo_enrolamiento)
    @cached_property
    def gestor_alertas(self): return GestorAlertas(self.alertas, self.autenticacion)
    @cached_property
    def recepcion(self):
        return ServicioRecepcionDatos(self.enrolamiento, self.equipos, self.lecturas,
                                      self.gestor_alertas, self.configuracion)
    @cached_property
    def disponibilidad(self):
        return ServicioDisponibilidad(self.equipos, self.gestor_alertas, self.cfg.intervalo_reporte_min)
    @cached_property
    def bitacora(self): return BitacoraAuditoria(self.registros_bitacora, self.autenticacion)
    @cached_property
    def acciones(self):
        return ServicioAcciones(self.comandos, self.equipos, self.enrolamiento, self.autenticacion, self.bitacora)
    @cached_property
    def parque(self): return ParqueComputacional(self.equipos, self.lecturas, self.alertas, self.autenticacion)


def obtener_bd(request: Request) -> Iterator[Session]:
    """Una transacción por petición: se confirma si todo salió bien y se revierte si hubo error,
    salvo los errores que piden conservar lo escrito (ErrorAplicacion.conservar_cambios)."""
    bd: Session = request.app.state.fabrica_sesiones()
    try:
        yield bd
        bd.commit()
    except ErrorAplicacion as error:
        bd.commit() if error.conservar_cambios else bd.rollback()
        raise
    except Exception:
        bd.rollback()
        raise
    finally:
        bd.close()


def obtener_contenedor(request: Request, bd: Session = Depends(obtener_bd)) -> Contenedor:
    return Contenedor(bd, request.app.state.cfg)


def _token_bearer(authorization: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


def sesion_actual(c: Contenedor = Depends(obtener_contenedor),
                  authorization: str | None = Header(default=None)) -> Sesion:
    """RF17: todo endpoint del panel exige una sesión válida (si no, 401)."""
    return c.autenticacion.validar_sesion(_token_bearer(authorization))


def token_agente(authorization: str | None = Header(default=None)) -> str | None:
    return _token_bearer(authorization)
