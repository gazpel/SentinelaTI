"""Dominio — acciones remotas (L4: clases_dominio_l4_acciones.puml).

Comando (abstracta) con herencia de tabla única. En el L5 se implementan
ComandoReinicioApagado (real en el agente, RF08) y ComandoFormateo (simulado,
RF11). Las demás subclases del diseño (instalación, actualización del SO y
escritorio remoto) quedan para el L6.

Ciclo de vida (L3 §3.8):
    Pendiente → Entregado → Ejecutado | Fallido
    Pendiente → Cancelado          (el técnico la cancela antes de la entrega)
    Pendiente | Entregado → Expirado (nadie la ejecutó a tiempo)
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, ErrorDominio, ahora, nuevo_id, tipo_enum
from .enumeraciones import EstadoComando, ModoApagado, TipoAccion
from .monitoreo import Equipo
from .usuarios import Usuario

# Plazos de expiración: una orden pendiente se descarta a las 24 h; una entregada,
# a los 60 min (5 min de aviso + 30 min de posposición de RF15 + margen).
VIGENCIA_PENDIENTE = timedelta(hours=24)
VIGENCIA_ENTREGADO = timedelta(minutes=60)


@dataclass(frozen=True)
class OrdenComando:
    """DTO sin comportamiento que viaja al agente (L4, cambio C2 y decisión D12)."""

    id_comando: str
    tipo: TipoAccion
    parametros: dict[str, str] = field(default_factory=dict)
    interrumpe_uso: bool = False
    simulado: bool = False


@dataclass(frozen=True)
class ResultadoEjecucion:
    exito: bool
    mensaje: str | None = None

    @property
    def estado(self) -> EstadoComando:
        return EstadoComando.EJECUTADO if self.exito else EstadoComando.FALLIDO


class TransicionInvalida(ErrorDominio):
    pass


class Comando(Base):
    __tablename__ = "comandos"

    id_comando: Mapped[str] = mapped_column(String(36), primary_key=True, default=nuevo_id)
    tipo_accion: Mapped[TipoAccion] = mapped_column(tipo_enum(TipoAccion))
    equipo_id: Mapped[str] = mapped_column(ForeignKey("equipos.id_equipo"), index=True)
    usuario_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id_usuario"))
    estado: Mapped[EstadoComando] = mapped_column(tipo_enum(EstadoComando), default=EstadoComando.PENDIENTE)
    fecha_orden: Mapped[datetime] = mapped_column(DateTime, default=ahora)
    fecha_entrega: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    fecha_resultado: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    motivo_fallo: Mapped[str | None] = mapped_column(Text, nullable=True)
    simulado: Mapped[bool] = mapped_column(Boolean, default=False)
    # Atributos propios de cada subclase (tabla única).
    modo: Mapped[ModoApagado | None] = mapped_column(tipo_enum(ModoApagado), nullable=True)
    nombre_confirmado: Mapped[str | None] = mapped_column(String(120), nullable=True)

    equipo: Mapped[Equipo] = relationship(lazy="joined")
    usuario: Mapped[Usuario] = relationship(lazy="joined")

    __mapper_args__ = {"polymorphic_on": "tipo_accion", "polymorphic_abstract": True}

    # ---- contrato que define cada subclase ---------------------------------------
    def tipo(self) -> TipoAccion:
        return TipoAccion(self.tipo_accion)

    def interrumpe_uso(self) -> bool:
        raise NotImplementedError

    def parametros(self) -> dict[str, str]:
        return {}

    def descripcion(self) -> str:
        raise NotImplementedError

    # ---- comportamiento común ----------------------------------------------------
    def a_orden(self) -> OrdenComando:
        return OrdenComando(
            id_comando=self.id_comando,
            tipo=self.tipo(),
            parametros=self.parametros(),
            interrumpe_uso=self.interrumpe_uso(),
            simulado=self.simulado,
        )

    def marcar_entregado(self, momento: datetime | None = None) -> None:
        self._exigir_estado(EstadoComando.PENDIENTE, "entregar")
        self.estado = EstadoComando.ENTREGADO
        self.fecha_entrega = momento or ahora()

    def registrar_resultado(self, r: ResultadoEjecucion, momento: datetime | None = None) -> None:
        self._exigir_estado(EstadoComando.ENTREGADO, "registrar el resultado de")
        self.estado = r.estado
        self.motivo_fallo = None if r.exito else (r.mensaje or "Sin detalle")
        self.fecha_resultado = momento or ahora()

    def cancelar(self, momento: datetime | None = None) -> None:
        self._exigir_estado(EstadoComando.PENDIENTE, "cancelar")
        self.estado = EstadoComando.CANCELADO
        self.fecha_resultado = momento or ahora()

    def ha_expirado(self, momento: datetime) -> bool:
        if self.estado == EstadoComando.PENDIENTE:
            return momento - self.fecha_orden > VIGENCIA_PENDIENTE
        if self.estado == EstadoComando.ENTREGADO:
            return momento - (self.fecha_entrega or self.fecha_orden) > VIGENCIA_ENTREGADO
        return False

    def expirar(self, momento: datetime | None = None) -> None:
        if self.estado not in (EstadoComando.PENDIENTE, EstadoComando.ENTREGADO):
            raise TransicionInvalida(f"No se puede expirar una orden en estado {self.estado.value}.")
        self.estado = EstadoComando.EXPIRADO
        self.fecha_resultado = momento or ahora()

    def _exigir_estado(self, esperado: EstadoComando, accion: str) -> None:
        if self.estado != esperado:
            raise TransicionInvalida(
                f"No se puede {accion} una orden en estado {EstadoComando(self.estado).value}.")


class ComandoReinicioApagado(Comando):
    """RF08. Real en el agente (con la salvaguarda de solo ejecutar en una VM de pruebas)."""

    __mapper_args__ = {"polymorphic_identity": TipoAccion.REINICIAR_APAGAR.value}

    def __init__(self, modo: ModoApagado, **kw):
        super().__init__(modo=modo, simulado=False, **kw)

    def interrumpe_uso(self) -> bool:
        return True

    def parametros(self) -> dict[str, str]:
        return {"modo": ModoApagado(self.modo).value}

    def descripcion(self) -> str:
        return "Reinicio" if self.modo == ModoApagado.REINICIAR else "Apagado"


class ComandoFormateo(Comando):
    """RF11. Simulado en el prototipo; exige escribir el nombre exacto del equipo."""

    __mapper_args__ = {"polymorphic_identity": TipoAccion.FORMATEAR.value}

    def __init__(self, nombre_confirmado: str, **kw):
        super().__init__(nombre_confirmado=nombre_confirmado, simulado=True, **kw)

    def confirmacion_valida(self, e: Equipo) -> bool:
        return (self.nombre_confirmado or "") == e.nombre

    def interrumpe_uso(self) -> bool:
        return True

    def descripcion(self) -> str:
        return "Formateo (simulado)"
