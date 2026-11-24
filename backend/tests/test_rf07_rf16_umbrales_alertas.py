"""RF07 (umbrales) y RF16 (alertas). Casos CP-18 a CP-21.

Entrada analizada con particiones de equivalencia: el par (advertencia, crítico) del
umbral de CPU, cuyo dominio válido es 1 ≤ advertencia < crítico ≤ 100.
"""
import pytest

from conftest import enrolar, enviar


@pytest.mark.parametrize("advertencia, critico, esperado", [
    (70, 90, 200),     # P1 válida: valores típicos
    (1, 2, 200),       # P1 válida: mínimo del dominio (límite)
    (99, 100, 200),    # P1 válida: máximo del dominio (límite)
    (89.9, 90, 200),   # P1 válida: crítico apenas mayor que advertencia (límite)
    (0, 90, 422),      # P2 inválida: advertencia bajo el mínimo (límite)
    (70, 100.1, 422),  # P3 inválida: crítico sobre el máximo (límite)
    (90, 90, 422),     # P4 inválida: crítico igual a advertencia (límite, criterio de RF07)
    (90, 70, 422),     # P4 inválida: crítico menor que advertencia
])
def test_cp18_particiones_del_umbral_de_cpu(cliente, h_admin, advertencia, critico, esperado):
    r = cliente.put("/api/panel/umbrales/CPU", headers=h_admin, json={"advertencia": advertencia, "critico": critico})
    assert r.status_code == esperado, r.text
    vigente = next(u for u in cliente.get("/api/panel/umbrales", headers=h_admin).json() if u["metrica"] == "CPU")
    if esperado == 200:
        assert (vigente["advertencia"], vigente["critico"]) == (advertencia, critico)
    else:  # un umbral rechazado no altera la configuración vigente
        assert (vigente["advertencia"], vigente["critico"]) == (80, 95)


def test_cp18b_metrica_inexistente_responde_422(cliente, h_admin):
    assert cliente.put("/api/panel/umbrales/Voltaje", headers=h_admin, json={"advertencia": 1, "critico": 2}).status_code == 422


def test_cp19_umbral_modificado_se_aplica_desde_la_lectura_siguiente(cliente, h_admin):
    id_equipo, h = enrolar(cliente)
    enviar(cliente, h, cpu=60)
    assert cliente.get(f"/api/panel/equipos/{id_equipo}", headers=h_admin).json()["estado"] == "Normal"
    cliente.put("/api/panel/umbrales/CPU", headers=h_admin, json={"advertencia": 50, "critico": 55})
    assert cliente.get(f"/api/panel/equipos/{id_equipo}", headers=h_admin).json()["estado"] == "Normal"  # aún no
    enviar(cliente, h, cpu=60)
    assert cliente.get(f"/api/panel/equipos/{id_equipo}", headers=h_admin).json()["estado"] == "Critico"


def _alertas(cliente, h_admin):
    return cliente.get("/api/panel/alertas", headers=h_admin).json()["items"]


def test_cp20_ciclo_de_vida_de_una_alerta(cliente, h_admin):
    """Criterio de RF16: sobre el umbral crea; una segunda lectura sobre el umbral no crea otra; bajo el umbral cierra."""
    _, h = enrolar(cliente)
    enviar(cliente, h, cpu=99)
    assert len(_alertas(cliente, h_admin)) == 1
    enviar(cliente, h, cpu=98)
    assert len(_alertas(cliente, h_admin)) == 1
    enviar(cliente, h, cpu=30)
    assert _alertas(cliente, h_admin) == []


@pytest.mark.parametrize("cpu, alertas, estado", [
    (80, 0, "Normal"),        # igual al umbral de advertencia: no lo supera
    (80.1, 0, "Advertencia"),
    (95, 0, "Advertencia"),   # igual al crítico: no lo supera (RF16: «supere»)
    (95.1, 1, "Critico"),
])
def test_cp21_valores_limite_en_los_umbrales_por_defecto(cliente, h_admin, cpu, alertas, estado):
    id_equipo, h = enrolar(cliente)
    enviar(cliente, h, cpu=cpu)
    assert len(_alertas(cliente, h_admin)) == alertas
    assert cliente.get(f"/api/panel/equipos/{id_equipo}", headers=h_admin).json()["estado"] == estado


def test_cp21b_una_alerta_por_equipo_y_metrica(cliente, h_admin):
    _, h = enrolar(cliente)
    enviar(cliente, h, cpu=99, ram=99, disco=99)
    assert sorted(a["metrica"] for a in _alertas(cliente, h_admin)) == ["CPU", "Disco", "RAM"]


def test_cp21c_lectura_atrasada_no_cambia_el_estado_actual(cliente, h_admin):
    """Una lectura que llega desde la cola local (más antigua que la última) solo va al historial."""
    from datetime import timedelta
    id_equipo, h = enrolar(cliente)
    enviar(cliente, h, cpu=20)
    enviar(cliente, h, cpu=99, hace=timedelta(hours=1))
    assert cliente.get(f"/api/panel/equipos/{id_equipo}", headers=h_admin).json()["estado"] == "Normal"
    assert _alertas(cliente, h_admin) == []
