"""RF01 (enrolamiento), RF02 (lecturas), RNF01 (token) y RNF04 (sin duplicados). Casos CP-09 a CP-14."""
from datetime import timedelta

import pytest

from conftest import CODIGO, enrolar, enviar, lectura


def test_cp09_enrolamiento_con_codigo_valido_aparece_en_el_listado(cliente, h_admin):
    id_equipo, _ = enrolar(cliente, "PC-NUEVO")
    listado = cliente.get("/api/panel/equipos", headers=h_admin).json()
    assert [e["idEquipo"] for e in listado["items"]] == [id_equipo]


def test_cp10_codigo_invalido_no_crea_registro(cliente, h_admin):
    r = cliente.post("/api/agente/enrolamiento", json={"codigo": CODIGO + "X", "nombre": "PC", "numeroSerie": "S"})
    assert r.status_code == 401
    assert cliente.get("/api/panel/equipos", headers=h_admin).json()["total"] == 0


def test_cp11_reenrolar_mismo_numero_de_serie_no_duplica_y_revoca_token(cliente, h_admin):
    id1, token_viejo = enrolar(cliente, "PC-A", serie="S-1")
    id2, token_nuevo = enrolar(cliente, "PC-A-renombrado", serie="S-1")
    assert id1 == id2
    assert cliente.get("/api/panel/equipos", headers=h_admin).json()["total"] == 1
    assert enviar(cliente, token_viejo).status_code == 401  # token revocado (RNF01)
    assert enviar(cliente, token_nuevo).status_code == 200


def test_cp12_lectura_valida_se_almacena_con_los_cinco_campos(cliente, h_admin):
    id_equipo, h = enrolar(cliente)
    assert enviar(cliente, h, cpu=12.5, ram=40, disco=70, temp=None, horas=3).json() == {"registrada": True, "duplicada": False}
    ultima = cliente.get(f"/api/panel/equipos/{id_equipo}", headers=h_admin).json()["ultimaLectura"]
    assert ultima["usoCpu"] == 12.5 and ultima["usoRam"] == 40 and ultima["usoDiscoMax"] == 70
    assert ultima["horasEncendido"] == 3
    assert ultima["temperaturaCpu"] is None  # «no disponible», no 0 (criterio de RF02)


def test_cp13_lectura_reenviada_no_se_duplica(cliente, h_admin):
    id_equipo, h = enrolar(cliente)
    cuerpo = lectura(hace=timedelta(minutes=10))
    assert cliente.post("/api/agente/lecturas", headers=h, json=cuerpo).json()["registrada"] is True
    assert cliente.post("/api/agente/lecturas", headers=h, json=cuerpo).json()["duplicada"] is True
    assert len(cliente.get(f"/api/panel/equipos/{id_equipo}/lecturas", headers=h_admin).json()) == 1


@pytest.mark.parametrize("cabecera", [None, "Bearer inventado"])
def test_cp14_lectura_sin_token_valido_responde_401(cliente, cabecera):
    enrolar(cliente)
    headers = {"Authorization": cabecera} if cabecera else {}
    assert cliente.post("/api/agente/lecturas", headers=headers, json=lectura()).status_code == 401


# Particiones de equivalencia y valores límite sobre uso de CPU (igual para RAM y disco): [0, 100].
@pytest.mark.parametrize("cpu, esperado", [
    (-0.1, 422),   # P1 inválida: bajo el mínimo (límite)
    (0, 200),      # P2 válida: mínimo
    (55.5, 200),   # P2 válida: valor típico
    (100, 200),    # P2 válida: máximo
    (100.1, 422),  # P3 inválida: sobre el máximo (límite)
])
def test_cp14b_particiones_uso_cpu(cliente, cpu, esperado):
    _, h = enrolar(cliente)
    assert enviar(cliente, h, cpu=cpu).status_code == esperado


@pytest.mark.parametrize("temp, esperado", [(None, 200), (0, 200), (150, 200), (150.1, 422), (-1, 422)])
def test_cp14c_particiones_temperatura(cliente, temp, esperado):
    _, h = enrolar(cliente)
    assert enviar(cliente, h, temp=temp).status_code == esperado


def test_cp14d_lectura_con_campos_extra_se_rechaza(cliente):
    """RNF05: el contrato solo admite los campos de RF02."""
    _, h = enrolar(cliente)
    cuerpo = {**lectura(), "historialNavegacion": ["sitio"]}
    assert cliente.post("/api/agente/lecturas", headers=h, json=cuerpo).status_code == 422


def test_cp14e_lectura_con_fecha_futura_se_rechaza(cliente):
    _, h = enrolar(cliente)
    assert enviar(cliente, h, hace=-timedelta(minutes=10)).status_code == 422
    assert enviar(cliente, h, hace=-timedelta(minutes=4)).status_code == 200  # dentro de la tolerancia de reloj
