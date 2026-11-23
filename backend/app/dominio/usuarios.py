"""Dominio — seguridad y usuarios (L4: clases_dominio_l4_usuarios.puml).

Usuario (abstracta) → Tecnico → Administrador, con herencia de tabla única.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import ClassVar

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, ahora, nuevo_id
from .enumeraciones import Permiso, Rol

MAX_INTENTOS_FALLIDOS = 5          # CU03, excepción 3b
MINUTOS_BLOQUEO = 15


class Usuario(Base):
    __tablename__ = "usuarios"

    id_usuario: Mapped[str] = mapped_column(String(36), primary_key=True, default=nuevo_id)
    nombre: Mapped[str] = mapped_column(String(120))
    correo: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    hash_contrasena: Mapped[str] = mapped_column(String(255))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    intentos_fallidos: Mapped[int] = mapped_column(Integer, default=0)
    bloqueado_hasta: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    tipo_rol: Mapped[str] = mapped_column(String(20))

    __mapper_args__ = {"polymorphic_on": "tipo_rol", "polymorphic_abstract": True}

    # Permisos de cada rol; las subclases los amplían (Tabla 5 del ERS).
    PERMISOS: ClassVar[frozenset[Permiso]] = frozenset()

    def rol(self) -> Rol:
        raise NotImplementedError

    def tiene_permiso(self, p: Permiso) -> bool:
        return p in self.PERMISOS

    def esta_bloqueado(self, momento: datetime | None = None) -> bool:
        momento = momento or ahora()
        return self.bloqueado_hasta is not None and self.bloqueado_hasta > momento

    def registrar_intento_fallido(self, momento: datetime | None = None) -> None:
        """Tras 5 intentos fallidos la cuenta queda bloqueada 15 minutos (CU03, 3b)."""
        momento = momento or ahora()
        self.intentos_fallidos += 1
        if self.intentos_fallidos >= MAX_INTENTOS_FALLIDOS:
            self.bloqueado_hasta = momento + timedelta(minutes=MINUTOS_BLOQUEO)
            self.intentos_fallidos = 0

    def registrar_ingreso_exitoso(self) -> None:
        self.intentos_fallidos = 0
        self.bloqueado_hasta = None

    def desactivar(self) -> None:
        self.activo = False


class Tecnico(Usuario):
    __mapper_args__ = {"polymorphic_identity": Rol.TECNICO.value}

    PERMISOS = frozenset({
        Permiso.CONSULTAR_PARQUE,
        Permiso.ORDENAR_ACCION,
        Permiso.CONSULTAR_BITACORA,
    })

    def rol(self) -> Rol:
        return Rol.TECNICO


class Administrador(Tecnico):
    __mapper_args__ = {"polymorphic_identity": Rol.ADMINISTRADOR.value}

    PERMISOS = Tecnico.PERMISOS | frozenset({
        Permiso.FORMATEAR,
        Permiso.CONFIGURAR_UMBRALES,
        Permiso.GESTIONAR_USUARIOS,
    })

    def rol(self) -> Rol:
        return Rol.ADMINISTRADOR


def clase_para_rol(rol: Rol) -> type[Usuario]:
    return Administrador if rol is Rol.ADMINISTRADOR else Tecnico


@dataclass
class Sesion:
    """Sesión del panel. En el prototipo no se persiste: vive dentro del JWT firmado
    (ver decisión L5-D3), y se reconstruye en cada petición."""

    id_sesion: str
    usuario: Usuario
    token_jwt: str
    fecha_expiracion: datetime

    def esta_vigente(self, momento: datetime | None = None) -> bool:
        return (momento or ahora()) < self.fecha_expiracion and self.usuario.activo
