"""Utilidades comunes de las pruebas de la API. Cada prueba usa una base SQLite en memoria nueva."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.config import Configuracion
from app.main import crear_app
from app.presentacion.dependencias import Contenedor

ADMIN = ("admin@prueba.cl", "Admin.Prueba1")
CODIGO = "CODIGO-PRUEBA"


@pytest.fixture
def cfg() -> Configuracion:
    c = Configuracion()
    c.url_bd = "sqlite://"
    c.tareas_periodicas = False
    c.codigo_enrolamiento = CODIGO
    c.correo_admin, c.clave_admin = ADMIN
    c.secreto_jwt = "secreto-de-pruebas-de-al-menos-32-bytes"
    return c


@pytest.fixture
def app(cfg):
    return crear_app(cfg)


@pytest.fixture
def cliente(app):
    with TestClient(app) as c:
        yield c


@pytest.fixture
def contenedor(app, cliente):
    """Acceso directo a los servicios (para mover el reloj en las pruebas de tiempo)."""
    bd = app.state.fabrica_sesiones()
    yield Contenedor(bd, app.state.cfg)
    bd.close()


def iniciar_sesion(cliente, correo, clave) -> dict:
    r = cliente.post("/api/panel/sesion", json={"correo": correo, "clave": clave})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture
def h_admin(cliente) -> dict:
    return iniciar_sesion(cliente, *ADMIN)


@pytest.fixture
def h_tecnico(cliente, h_admin) -> dict:
    r = cliente.post("/api/panel/usuarios", headers=h_admin,
                     json={"nombre": "Técnico Uno", "correo": "tec@prueba.cl", "rol": "Tecnico", "clave": "Tecnico.123"})
    assert r.status_code == 201, r.text
    return iniciar_sesion(cliente, "tec@prueba.cl", "Tecnico.123")


def enrolar(cliente, nombre="PC-PRUEBA-01", serie=None, ip="10.0.0.1", usuario="usuario1") -> tuple[str, dict]:
    r = cliente.post("/api/agente/enrolamiento", json={
        "codigo": CODIGO, "nombre": nombre, "numeroSerie": serie or f"SERIE-{nombre}",
        "direccionIp": ip, "ultimoUsuario": usuario})
    assert r.status_code == 201, r.text
    return r.json()["idEquipo"], {"Authorization": f"Bearer {r.json()['token']}"}


def lectura(cpu=20.0, ram=30.0, disco=40.0, temp=50.0, horas=5.0, hace=timedelta(0)) -> dict:
    marca = datetime.now(timezone.utc) - hace
    return {"marcaTiempo": marca.isoformat(), "usoCpu": cpu, "usoRam": ram,
            "discos": [{"unidad": "C:", "usoPorcentaje": disco}], "temperaturaCpu": temp, "horasEncendido": horas}


def enviar(cliente, h_agente, **kw):
    return cliente.post("/api/agente/lecturas", headers=h_agente, json=lectura(**kw))
