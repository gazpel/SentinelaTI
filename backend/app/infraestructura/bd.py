"""Conexión a la base de datos (capa de infraestructura)."""
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.dominio.base import Base


def crear_motor(url: str) -> Engine:
    if url.startswith("sqlite"):
        opciones = {"connect_args": {"check_same_thread": False}}
        if url in ("sqlite://", "sqlite:///:memory:"):
            opciones["poolclass"] = StaticPool  # una sola conexión compartida (pruebas)
        motor = create_engine(url, **opciones)

        @event.listens_for(motor, "connect")
        def _activar_claves_foraneas(conexion, _):
            conexion.execute("PRAGMA foreign_keys=ON")

        return motor
    return create_engine(url, pool_pre_ping=True)


def crear_tablas(motor: Engine) -> None:
    import app.dominio  # noqa: F401  (registra todas las entidades en Base.metadata)
    Base.metadata.create_all(motor)


def fabrica_sesiones(motor: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=motor, expire_on_commit=False)
