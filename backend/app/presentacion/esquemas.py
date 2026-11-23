"""Esquemas JSON de la API (contrato IPanelAPI e IAgenteAPI del L4).

Los nombres viajan en camelCase. Las fechas se guardan en UTC sin zona y se
publican en ISO 8601 con «Z».
"""
from datetime import datetime, timezone
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer
from pydantic.alias_generators import to_camel

from app.dominio.enumeraciones import EstadoComando, EstadoEquipo, Metrica, NivelAlerta, Rol, TipoAccion


def _a_iso_utc(d: datetime) -> str:
    return d.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


FechaUTC = Annotated[datetime, PlainSerializer(_a_iso_utc, return_type=str)]
Porcentaje = Annotated[float, Field(ge=0, le=100)]


class Esquema(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


# ---------------------------------------------------------------------------- panel
class SolicitudInicioSesion(Esquema):
    correo: str = Field(min_length=3, max_length=254)
    clave: str = Field(min_length=1, max_length=200)


class UsuarioSalida(Esquema):
    id_usuario: str
    nombre: str
    correo: str
    rol: Rol
    activo: bool
    permisos: list[str]


class SesionSalida(Esquema):
    token: str
    expira: FechaUTC
    usuario: UsuarioSalida


class UsuarioEntrada(Esquema):
    nombre: str
    correo: str
    rol: Rol
    clave: str


class UsuarioEdicion(Esquema):
    nombre: str
    rol: Rol


class EquipoResumen(Esquema):
    id_equipo: str
    nombre: str
    direccion_ip: str | None
    ultimo_usuario: str | None
    estado: EstadoEquipo
    fecha_ultimo_reporte: FechaUTC | None


class ListadoEquipos(Esquema):
    items: list[EquipoResumen]
    total: int
    pagina: int
    tamano: int
    resumen: dict[EstadoEquipo, int]
    alertas_abiertas: int


class UsoDiscoSalida(Esquema):
    unidad: str
    uso_porcentaje: float


class LecturaSalida(Esquema):
    marca_tiempo: FechaUTC
    uso_cpu: float
    uso_ram: float
    temperatura_cpu: float | None
    horas_encendido: float
    discos: list[UsoDiscoSalida]
    uso_disco_max: float | None


class AlertaSalida(Esquema):
    id_alerta: str
    id_equipo: str
    nombre_equipo: str
    metrica: Metrica | None
    nivel: NivelAlerta
    valor: float | None
    fecha_apertura: FechaUTC


class ListadoAlertas(Esquema):
    items: list[AlertaSalida]
    total: int


class EquipoDetalle(EquipoResumen):
    numero_serie: str
    modelo: str | None
    sistema_operativo: str | None
    fecha_enrolamiento: FechaUTC
    ultima_lectura: LecturaSalida | None
    alertas_abiertas: list[AlertaSalida]


class UmbralSalida(Esquema):
    metrica: Metrica
    advertencia: float
    critico: float
    minimo: float
    maximo: float
    unidad: str


class UmbralEntrada(Esquema):
    advertencia: float
    critico: float


class ComandoEntrada(Esquema):
    tipo: TipoAccion
    modo: str | None = None
    nombre_confirmado: str | None = None


class ComandoSalida(Esquema):
    id_comando: str
    id_equipo: str
    nombre_equipo: str
    tipo: TipoAccion
    descripcion: str
    estado: EstadoComando
    simulado: bool
    ordenado_por: str
    fecha_orden: FechaUTC
    fecha_entrega: FechaUTC | None
    fecha_resultado: FechaUTC | None
    motivo_fallo: str | None


class EntradaBitacoraSalida(Esquema):
    id_entrada: str
    fecha_orden: FechaUTC
    fecha_resultado: FechaUTC | None
    tipo_accion: TipoAccion
    descripcion: str
    estado_resultante: EstadoComando
    nombre_usuario: str
    nombre_equipo: str
    cerrada: bool


# ---------------------------------------------------------------------------- agente
class EnrolamientoEntrada(Esquema):
    codigo: str = Field(min_length=1, max_length=100)
    nombre: str = Field(min_length=1, max_length=120)
    numero_serie: str = Field(min_length=1, max_length=120)
    modelo: str | None = Field(default=None, max_length=120)
    sistema_operativo: str | None = Field(default=None, max_length=120)
    direccion_ip: str | None = Field(default=None, max_length=45)
    ultimo_usuario: str | None = Field(default=None, max_length=120)


class EnrolamientoSalida(Esquema):
    id_equipo: str
    token: str
    intervalo_reporte_min: int


class UsoDiscoEntrada(Esquema):
    unidad: str = Field(min_length=1, max_length=10)
    uso_porcentaje: Porcentaje


class LecturaEntrada(Esquema):
    """Contrato de la lectura (RF02). Solo estos campos: el agente no puede enviar otros datos (RNF05)."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")

    marca_tiempo: datetime
    uso_cpu: Porcentaje
    uso_ram: Porcentaje
    discos: list[UsoDiscoEntrada] = Field(min_length=1, max_length=26)
    temperatura_cpu: float | None = Field(default=None, ge=0, le=150)  # None = «no disponible»
    horas_encendido: float = Field(ge=0, le=100_000)


class RespuestaLectura(Esquema):
    registrada: bool
    duplicada: bool


class OrdenSalida(Esquema):
    id_comando: str
    tipo: TipoAccion
    parametros: dict[str, str]
    interrumpe_uso: bool
    simulado: bool


class ResultadoEntrada(Esquema):
    exito: bool
    mensaje: str | None = Field(default=None, max_length=500)
