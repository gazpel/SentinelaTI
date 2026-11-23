"""Elementos comunes del modelo de dominio.

Decisión L5 (ver docs/L5): las entidades del dominio se declaran con el mapeo
declarativo de SQLAlchemy para no duplicar cada clase en un modelo ORM aparte.
La única dependencia del dominio con la infraestructura son esos metadatos de
mapeo; las consultas y la sesión de base de datos viven solo en
``app.infraestructura`` detrás de los contratos de ``app.dominio.repositorios``.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class ErrorDominio(Exception):
    """Violación de una regla del dominio (la API la traduce a HTTP 409 o 422)."""


def nuevo_id() -> str:
    return str(uuid.uuid4())


def ahora() -> datetime:
    """Hora actual en UTC, sin zona horaria (SQLite no conserva la zona)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def tipo_enum(clase_enum: type, largo: int = 20) -> SAEnum:
    """Columna que guarda el *valor* de la enumeración como texto (portable a SQLite y PostgreSQL)."""
    return SAEnum(clase_enum, native_enum=False, length=largo,
                  values_callable=lambda e: [m.value for m in e])
