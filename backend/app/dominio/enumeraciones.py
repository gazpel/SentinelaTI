"""Enumeraciones del dominio (L3: clases_enumeraciones.puml; L4: Permiso y TipoAccion.permisoRequerido()).

Los valores se guardan como texto en la base de datos y viajan tal cual en el JSON
de la API, por eso cada miembro hereda de ``str``.
"""
from enum import Enum


class Rol(str, Enum):
    TECNICO = "Tecnico"
    ADMINISTRADOR = "Administrador"


class Permiso(str, Enum):
    """Filas de la Tabla 5 del ERS (matriz de permisos por rol, RNF07)."""

    CONSULTAR_PARQUE = "ConsultarParque"
    ORDENAR_ACCION = "OrdenarAccion"
    FORMATEAR = "Formatear"
    CONFIGURAR_UMBRALES = "ConfigurarUmbrales"
    GESTIONAR_USUARIOS = "GestionarUsuarios"
    CONSULTAR_BITACORA = "ConsultarBitacora"


class EstadoEquipo(str, Enum):
    NORMAL = "Normal"
    ADVERTENCIA = "Advertencia"
    CRITICO = "Critico"
    DESCONECTADO = "Desconectado"

    @property
    def severidad(self) -> int:
        """Orden del listado del parque (RNF06): Crítico, Advertencia, Desconectado, Normal."""
        return _SEVERIDAD[self]


_SEVERIDAD = {
    EstadoEquipo.CRITICO: 0,
    EstadoEquipo.ADVERTENCIA: 1,
    EstadoEquipo.DESCONECTADO: 2,
    EstadoEquipo.NORMAL: 3,
}


class NivelAlerta(str, Enum):
    NORMAL = "Normal"
    ADVERTENCIA = "Advertencia"
    CRITICO = "Critico"


class Metrica(str, Enum):
    """Las cinco métricas de RF02."""

    CPU = "CPU"
    RAM = "RAM"
    DISCO = "Disco"
    TEMPERATURA = "Temperatura"
    HORAS_ENCENDIDO = "HorasEncendido"


class EstadoComando(str, Enum):
    """Ciclo de vida del comando (L3 §3.8).

    ``DENEGADO`` se agregó en el L5: solo lo usan las entradas de bitácora de un
    intento sin permiso (registrarIntentoDenegado), nunca un Comando.
    """

    PENDIENTE = "Pendiente"
    ENTREGADO = "Entregado"
    EJECUTADO = "Ejecutado"
    FALLIDO = "Fallido"
    CANCELADO = "Cancelado"
    EXPIRADO = "Expirado"
    DENEGADO = "Denegado"

    @property
    def es_final(self) -> bool:
        return self not in (EstadoComando.PENDIENTE, EstadoComando.ENTREGADO)


class TipoAccion(str, Enum):
    REINICIAR_APAGAR = "ReiniciarApagar"
    INSTALAR_APP = "InstalarApp"
    ACTUALIZAR_SO = "ActualizarSO"
    FORMATEAR = "Formatear"
    ESCRITORIO_REMOTO = "EscritorioRemoto"

    def permiso_requerido(self) -> Permiso:
        """TipoAccion → Permiso (L4, D7): el formateo exige un permiso exclusivo del Administrador."""
        if self is TipoAccion.FORMATEAR:
            return Permiso.FORMATEAR
        return Permiso.ORDENAR_ACCION


class ModoApagado(str, Enum):
    REINICIAR = "Reiniciar"
    APAGAR = "Apagar"
