"""Dominio — auditoría (L4: paquete «Auditoría»; RF14, RF18, RNF12).

Una EntradaBitacora por comando: se abre al ordenar (registrarOrden) y se
cierra una sola vez con el resultado (cerrarEntrada). Después es inmutable.
"""
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, ErrorDominio, ahora, nuevo_id, tipo_enum
from .enumeraciones import EstadoComando, TipoAccion


class EntradaBitacora(Base):
    __tablename__ = "bitacora"

    id_entrada: Mapped[str] = mapped_column(String(36), primary_key=True, default=nuevo_id)
    # Sin clave foránea a propósito: la entrada debe sobrevivir aunque el comando se depure
    # (retención de 12 meses, RNF12) y se escribe antes que el comando (D11).
    comando_id: Mapped[str | None] = mapped_column(String(36), nullable=True, unique=True)
    fecha_orden: Mapped[datetime] = mapped_column(DateTime, default=ahora, index=True)
    fecha_resultado: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    tipo_accion: Mapped[TipoAccion] = mapped_column(tipo_enum(TipoAccion), index=True)
    descripcion: Mapped[str] = mapped_column(String(60))
    estado_resultante: Mapped[EstadoComando] = mapped_column(tipo_enum(EstadoComando))
    # Se copian el nombre del usuario y del equipo: la entrada sigue siendo legible
    # aunque el usuario se desactive o el equipo cambie de nombre (RNF12).
    usuario_id: Mapped[str] = mapped_column(String(36), index=True)
    nombre_usuario: Mapped[str] = mapped_column(String(120))
    equipo_id: Mapped[str] = mapped_column(String(36), index=True)
    nombre_equipo: Mapped[str] = mapped_column(String(120))
    cerrada: Mapped[bool] = mapped_column(Boolean, default=False)

    def cerrar(self, estado: EstadoComando, momento: datetime | None = None) -> None:
        if self.cerrada:
            raise ErrorDominio("La entrada de bitácora ya está cerrada y no se puede modificar (RNF12).")
        if not EstadoComando(estado).es_final:
            raise ErrorDominio("Una entrada solo se cierra con un resultado final.")
        self.estado_resultante = estado
        self.fecha_resultado = momento or ahora()
        self.cerrada = True

    def es_inmutable(self) -> bool:
        return self.cerrada


@dataclass(frozen=True)
class FiltroBitacora:
    """Filtros de RF18. Todos son opcionales y se combinan con Y lógico."""

    equipo_id: str | None = None
    usuario_id: str | None = None
    tipo_accion: TipoAccion | None = None
    desde: datetime | None = None
    hasta: datetime | None = None

    def es_valido(self) -> bool:
        return not (self.desde and self.hasta and self.desde > self.hasta)
