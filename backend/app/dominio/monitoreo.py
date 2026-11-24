"""Dominio — monitoreo del parque (L4: clases_dominio_l4_monitoreo.puml).

Clases: Equipo, TokenAgente, Lectura, UsoDisco, Alerta, Umbral y
ConfiguracionUmbrales. ParqueComputacional no es una clase en el código: sus
consultas (listar, buscar, resumenPorEstado) las resuelve EquipoRepository
(decisión D6 del L4), porque en el prototipo existe un solo parque.
"""
import hashlib
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, ErrorDominio, ahora, nuevo_id, tipo_enum
from .enumeraciones import EstadoEquipo, Metrica, NivelAlerta


def hash_token(valor_plano: str) -> str:
    """El servidor guarda solo el hash del token del agente (RNF01)."""
    return hashlib.sha256(valor_plano.encode()).hexdigest()


class Equipo(Base):
    __tablename__ = "equipos"

    id_equipo: Mapped[str] = mapped_column(String(36), primary_key=True, default=nuevo_id)
    nombre: Mapped[str] = mapped_column(String(120), index=True)
    numero_serie: Mapped[str] = mapped_column(String(120), unique=True)
    modelo: Mapped[str | None] = mapped_column(String(120), nullable=True)
    sistema_operativo: Mapped[str | None] = mapped_column(String(120), nullable=True)
    direccion_ip: Mapped[str | None] = mapped_column(String(45), nullable=True, index=True)
    ultimo_usuario: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    estado: Mapped[EstadoEquipo] = mapped_column(tipo_enum(EstadoEquipo), default=EstadoEquipo.NORMAL)
    # Copia numérica de la severidad del estado, para ordenar el listado en SQL (D6).
    severidad: Mapped[int] = mapped_column(default=EstadoEquipo.NORMAL.severidad, index=True)
    fecha_enrolamiento: Mapped[datetime] = mapped_column(DateTime, default=ahora)
    fecha_ultimo_reporte: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    tokens: Mapped[list["TokenAgente"]] = relationship(
        back_populates="equipo", cascade="all, delete-orphan")
    ultima_lectura = None  # no persistente: la lectura recién recibida, para evaluar_estado()

    # ---- operaciones del diseño -------------------------------------------------
    def registrar_lectura(self, lectura: "Lectura") -> None:
        lectura.equipo_id = self.id_equipo
        if self.fecha_ultimo_reporte is None or lectura.marca_tiempo >= self.fecha_ultimo_reporte:
            self.fecha_ultimo_reporte = lectura.marca_tiempo
            self.ultima_lectura = lectura

    def evaluar_estado(self, configuracion: "ConfiguracionUmbrales") -> EstadoEquipo:
        """Estado precalculado (D6): el peor nivel entre las métricas de la última lectura."""
        if self.ultima_lectura is None:
            return self.estado
        niveles = configuracion.evaluar_lectura(self.ultima_lectura).values()
        if NivelAlerta.CRITICO in niveles:
            nuevo = EstadoEquipo.CRITICO
        elif NivelAlerta.ADVERTENCIA in niveles:
            nuevo = EstadoEquipo.ADVERTENCIA
        else:
            nuevo = EstadoEquipo.NORMAL
        self._cambiar_estado(nuevo)
        return nuevo

    def marcar_desconectado(self) -> None:
        self._cambiar_estado(EstadoEquipo.DESCONECTADO)

    def esta_en_linea(self) -> bool:
        return self.estado != EstadoEquipo.DESCONECTADO

    def emitir_token(self, valor_plano: str) -> "TokenAgente":
        """Revoca el token vigente y emite uno nuevo (reenrolamiento del mismo número de serie)."""
        self.revocar_token_vigente()
        token = TokenAgente(valor=hash_token(valor_plano))
        self.tokens.append(token)
        return token

    def revocar_token_vigente(self) -> None:
        for token in self.tokens:
            token.revocado = True

    def _cambiar_estado(self, nuevo: EstadoEquipo) -> None:
        self.estado = EstadoEquipo(nuevo)
        self.severidad = self.estado.severidad


class TokenAgente(Base):
    __tablename__ = "tokens_agente"

    id_token: Mapped[str] = mapped_column(String(36), primary_key=True, default=nuevo_id)
    equipo_id: Mapped[str] = mapped_column(ForeignKey("equipos.id_equipo"))
    valor: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    revocado: Mapped[bool] = mapped_column(Boolean, default=False)
    fecha_emision: Mapped[datetime] = mapped_column(DateTime, default=ahora)

    equipo: Mapped[Equipo] = relationship(back_populates="tokens")

    def es_valido(self) -> bool:
        return not self.revocado


class Lectura(Base):
    __tablename__ = "lecturas"
    # La marca de tiempo original identifica la lectura: un reenvío desde la cola
    # local del agente no crea duplicados (RNF04).
    __table_args__ = (UniqueConstraint("equipo_id", "marca_tiempo"),)

    id_lectura: Mapped[str] = mapped_column(String(36), primary_key=True, default=nuevo_id)
    equipo_id: Mapped[str] = mapped_column(ForeignKey("equipos.id_equipo"), index=True)
    marca_tiempo: Mapped[datetime] = mapped_column(DateTime, index=True)
    uso_cpu: Mapped[float] = mapped_column(Float)
    uso_ram: Mapped[float] = mapped_column(Float)
    temperatura_cpu: Mapped[float | None] = mapped_column(Float, nullable=True)  # None = «no disponible»
    horas_encendido: Mapped[float] = mapped_column(Float)

    discos: Mapped[list["UsoDisco"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin")

    def valor_de(self, m: Metrica) -> float | None:
        """Valor de una métrica. Para el disco se usa la unidad más llena."""
        if m is Metrica.CPU:
            return self.uso_cpu
        if m is Metrica.RAM:
            return self.uso_ram
        if m is Metrica.DISCO:
            return max((d.uso_porcentaje for d in self.discos), default=None)
        if m is Metrica.TEMPERATURA:
            return self.temperatura_cpu
        return self.horas_encendido


class UsoDisco(Base):
    __tablename__ = "usos_disco"

    id_uso: Mapped[str] = mapped_column(String(36), primary_key=True, default=nuevo_id)
    lectura_id: Mapped[str] = mapped_column(ForeignKey("lecturas.id_lectura"), index=True)
    unidad: Mapped[str] = mapped_column(String(10))
    uso_porcentaje: Mapped[float] = mapped_column(Float)


class Alerta(Base):
    __tablename__ = "alertas"

    id_alerta: Mapped[str] = mapped_column(String(36), primary_key=True, default=nuevo_id)
    equipo_id: Mapped[str] = mapped_column(ForeignKey("equipos.id_equipo"), index=True)
    metrica: Mapped[Metrica | None] = mapped_column(tipo_enum(Metrica), nullable=True)  # None = desconexión
    nivel: Mapped[NivelAlerta] = mapped_column(tipo_enum(NivelAlerta))
    valor: Mapped[float | None] = mapped_column(Float, nullable=True)
    fecha_apertura: Mapped[datetime] = mapped_column(DateTime, default=ahora)
    fecha_cierre: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    equipo: Mapped[Equipo] = relationship(lazy="joined")

    def esta_abierta(self) -> bool:
        return self.fecha_cierre is None

    def cerrar(self, momento: datetime | None = None) -> None:
        if self.esta_abierta():
            self.fecha_cierre = momento or ahora()


# ---- Umbrales (RF07) ---------------------------------------------------------------

@dataclass(frozen=True)
class RangoMetrica:
    minimo: float
    maximo: float
    unidad: str


# Dominio válido de cada umbral. Es la entrada sobre la que se definen las
# particiones de equivalencia del esbozo del plan de pruebas (docs/L5).
RANGOS_UMBRAL: dict[Metrica, RangoMetrica] = {
    Metrica.CPU: RangoMetrica(1, 100, "%"),
    Metrica.RAM: RangoMetrica(1, 100, "%"),
    Metrica.DISCO: RangoMetrica(1, 100, "%"),
    Metrica.TEMPERATURA: RangoMetrica(1, 150, "°C"),
    Metrica.HORAS_ENCENDIDO: RangoMetrica(1, 8760, "h"),
}


class Umbral(Base):
    __tablename__ = "umbrales"

    metrica: Mapped[Metrica] = mapped_column(tipo_enum(Metrica), primary_key=True)
    valor_advertencia: Mapped[float] = mapped_column(Float)
    valor_critico: Mapped[float] = mapped_column(Float)

    def evaluar(self, valor: float | None) -> NivelAlerta:
        """Un valor *supera* el umbral cuando es estrictamente mayor (RF16: «supere»)."""
        if valor is None:
            return NivelAlerta.NORMAL
        if valor > self.valor_critico:
            return NivelAlerta.CRITICO
        if valor > self.valor_advertencia:
            return NivelAlerta.ADVERTENCIA
        return NivelAlerta.NORMAL

    def validar(self) -> None:
        rango = RANGOS_UMBRAL[self.metrica]
        for nombre, valor in (("advertencia", self.valor_advertencia), ("crítico", self.valor_critico)):
            if not (rango.minimo <= valor <= rango.maximo):
                raise ErrorDominio(
                    f"El umbral {nombre} de {self.metrica.value} debe estar entre "
                    f"{rango.minimo:g} y {rango.maximo:g} {rango.unidad}.")
        if self.valor_critico <= self.valor_advertencia:
            raise ErrorDominio("El umbral crítico debe ser mayor que el de advertencia (RF07).")


UMBRALES_POR_DEFECTO: dict[Metrica, tuple[float, float]] = {
    Metrica.CPU: (80, 95),
    Metrica.RAM: (80, 95),
    Metrica.DISCO: (85, 95),
    Metrica.TEMPERATURA: (75, 90),
    Metrica.HORAS_ENCENDIDO: (168, 720),
}


class ConfiguracionUmbrales:
    """Agrupa los cinco umbrales vigentes (composición 1 → 5 del L4)."""

    def __init__(self, umbrales: list[Umbral]):
        self._umbrales = {u.metrica: u for u in umbrales}

    def umbral_de(self, m: Metrica) -> Umbral:
        return self._umbrales[m]

    def umbrales(self) -> list[Umbral]:
        return [self._umbrales[m] for m in Metrica if m in self._umbrales]

    def validar(self) -> bool:
        if set(self._umbrales) != set(Metrica):
            raise ErrorDominio("La configuración debe tener un umbral por cada métrica.")
        for u in self._umbrales.values():
            u.validar()
        return True

    def evaluar_lectura(self, lectura: Lectura) -> dict[Metrica, NivelAlerta]:
        return {m: u.evaluar(lectura.valor_de(m)) for m, u in self._umbrales.items()}
