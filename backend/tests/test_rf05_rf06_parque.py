"""RF05 (listado, búsqueda y filtro), RF06 (historial por rango) y estado Desconectado. Casos CP-15 a CP-17."""
from datetime import timedelta

import pytest

from app.dominio.base import ahora
from conftest import enrolar, enviar


@pytest.fixture
def parque_de_20(cliente):
    """20 equipos: 2 críticos (CPU 99), 3 en advertencia (RAM 85), el resto normales."""
    for i in range(20):
        _, h = enrolar(cliente, f"PC-{i:02d}", ip=f"10.0.0.{i}", usuario=f"usuario{i:02d}")
        if i < 2:
            enviar(cliente, h, cpu=99)
        elif i < 5:
            enviar(cliente, h, ram=85)
        else:
            enviar(cliente, h)


def _nombres(cliente, h, **parametros):
    r = cliente.get("/api/panel/equipos", headers=h, params={"tamano": 100, **parametros})
    assert r.status_code == 200, r.text
    return [e["nombre"] for e in r.json()["items"]]


def test_cp15_filtro_por_estado_devuelve_exactamente_los_esperados(cliente, h_admin, parque_de_20):
    assert _nombres(cliente, h_admin, estado="Critico") == ["PC-00", "PC-01"]
    assert _nombres(cliente, h_admin, estado="Advertencia") == ["PC-02", "PC-03", "PC-04"]
    assert len(_nombres(cliente, h_admin, estado="Normal")) == 15
    assert _nombres(cliente, h_admin, estado="Desconectado") == []


@pytest.mark.parametrize("texto, esperados", [
    ("PC-1", [f"PC-1{i}" for i in range(10)]),  # por nombre
    ("10.0.0.7", ["PC-07"]),                     # por IP
    ("usuario03", ["PC-03"]),                    # por último usuario
    ("USUARIO03", ["PC-03"]),                    # sin distinguir mayúsculas
    ("no-existe", []),                           # sin coincidencias (CU04 4a)
])
def test_cp15b_busqueda_por_nombre_ip_o_usuario(cliente, h_admin, parque_de_20, texto, esperados):
    assert sorted(_nombres(cliente, h_admin, texto=texto)) == sorted(esperados)


def test_cp15c_listado_ordenado_por_severidad_y_resumen(cliente, h_admin, parque_de_20):
    r = cliente.get("/api/panel/equipos", headers=h_admin, params={"tamano": 10}).json()
    estados = [e["estado"] for e in r["items"]]
    assert estados[:5] == ["Critico", "Critico", "Advertencia", "Advertencia", "Advertencia"]
    assert r["total"] == 20 and len(r["items"]) == 10
    assert r["resumen"] == {"Critico": 2, "Advertencia": 3, "Desconectado": 0, "Normal": 15}


@pytest.mark.parametrize("pagina, tamano, esperado", [(0, 25, 422), (1, 0, 422), (1, 100, 200), (1, 101, 422)])
def test_cp15d_parametros_de_paginacion(cliente, h_admin, pagina, tamano, esperado):
    assert cliente.get("/api/panel/equipos", headers=h_admin, params={"pagina": pagina, "tamano": tamano}).status_code == esperado


def test_cp16_historial_muestra_solo_lecturas_del_rango(cliente, h_admin):
    id_equipo, h = enrolar(cliente)
    for hace in (timedelta(hours=1), timedelta(hours=23, minutes=58), timedelta(hours=24, minutes=2),
                 timedelta(days=6, hours=23), timedelta(days=7, hours=1), timedelta(days=29)):
        assert enviar(cliente, h, hace=hace).status_code == 200
    cantidad = {r: len(cliente.get(f"/api/panel/equipos/{id_equipo}/lecturas", headers=h_admin, params={"rango": r}).json())
                for r in ("24h", "7d", "30d")}
    assert cantidad == {"24h": 2, "7d": 4, "30d": 6}
    assert cliente.get(f"/api/panel/equipos/{id_equipo}/lecturas", headers=h_admin, params={"rango": "1a"}).status_code == 422


def test_cp17_equipo_sin_reportes_pasa_a_desconectado_con_alerta(cliente, contenedor, h_admin):
    """Valor límite: 3 intervalos de 5 min sin reporte todavía no desconecta; pasado ese límite, sí."""
    id_equipo, h = enrolar(cliente)
    enviar(cliente, h)
    ultimo = contenedor.equipos.obtener_por_id(id_equipo).fecha_ultimo_reporte
    assert contenedor.disponibilidad.detectar_desconectados(ultimo + timedelta(minutes=15)) == []
    marcados = contenedor.disponibilidad.detectar_desconectados(ultimo + timedelta(minutes=15, seconds=1))
    contenedor.bd.commit()
    assert [e.id_equipo for e in marcados] == [id_equipo]
    detalle = cliente.get(f"/api/panel/equipos/{id_equipo}", headers=h_admin).json()
    assert detalle["estado"] == "Desconectado"
    assert [a["metrica"] for a in detalle["alertasAbiertas"]] == [None]
    # Al volver a reportar, recupera su estado y la alerta de desconexión se cierra.
    enviar(cliente, h)
    detalle = cliente.get(f"/api/panel/equipos/{id_equipo}", headers=h_admin).json()
    assert detalle["estado"] == "Normal" and detalle["alertasAbiertas"] == []


def test_detalle_de_equipo_inexistente_responde_404(cliente, h_admin):
    assert cliente.get("/api/panel/equipos/no-existe", headers=h_admin).status_code == 404
