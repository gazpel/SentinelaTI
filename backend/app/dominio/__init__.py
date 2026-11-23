"""Capa de dominio de SentinelaTI (L4 §3.8)."""
from .acciones import Comando, ComandoFormateo, ComandoReinicioApagado, OrdenComando, ResultadoEjecucion
from .auditoria import EntradaBitacora, FiltroBitacora
from .base import Base, ErrorDominio
from .monitoreo import Alerta, ConfiguracionUmbrales, Equipo, Lectura, TokenAgente, Umbral, UsoDisco
from .usuarios import Administrador, Sesion, Tecnico, Usuario

__all__ = [
    "Administrador", "Alerta", "Base", "Comando", "ComandoFormateo", "ComandoReinicioApagado",
    "ConfiguracionUmbrales", "EntradaBitacora", "Equipo", "ErrorDominio", "FiltroBitacora",
    "Lectura", "OrdenComando", "ResultadoEjecucion", "Sesion", "Tecnico", "TokenAgente",
    "Umbral", "Usuario", "UsoDisco",
]
