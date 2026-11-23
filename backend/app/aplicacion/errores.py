"""Errores de la capa de aplicación. La capa de presentación los traduce a códigos HTTP."""
from app.dominio.base import ErrorDominio


class ErrorAplicacion(Exception):
    """Base de los errores de aplicación.

    ``conservar_cambios`` indica que lo escrito antes del error debe confirmarse
    igual en la base de datos: el intento fallido de inicio de sesión (CU03 3b) y
    la entrada de bitácora de un intento sin permiso (registrarIntentoDenegado).
    """

    def __init__(self, mensaje: str, conservar_cambios: bool = False):
        super().__init__(mensaje)
        self.conservar_cambios = conservar_cambios


class NoAutenticado(ErrorAplicacion):
    """Sin sesión válida o token de agente inválido/revocado → 401 (RF17, RNF01)."""


class CuentaBloqueada(NoAutenticado):
    """Cinco intentos fallidos seguidos (CU03, 3b) → 423."""


class PermisoDenegado(ErrorAplicacion):
    """El rol de la sesión no tiene el permiso → 403 (RNF07)."""

    def __init__(self, mensaje: str = "No tiene permiso para esta acción.", conservar_cambios: bool = False):
        super().__init__(mensaje, conservar_cambios)


class NoEncontrado(ErrorAplicacion):
    """→ 404"""


class DatosInvalidos(ErrorDominio):
    """Regla de negocio violada por los datos recibidos → 422."""
