"""RF08 (reinicio/apagado), RF11 (formateo), RF14 (bitácora) y RF18 (consulta). Casos CP-22 a CP-28."""
from datetime import datetime, timedelta, timezone

import pytest

from app.dominio.base import ahora
from conftest import enrolar


def ordenar(cliente, h, id_equipo, **cuerpo):
    return cliente.post(f"/api/panel/equipos/{id_equipo}/comandos", headers=h, json=cuerpo)


def pendientes(cliente, h_agente):
    return cliente.get("/api/agente/comandos/pendientes", headers=h_agente).json()


def informar(cliente, h_agente, id_comando, exito=True, mensaje=None):
    return cliente.post(f"/api/agente/comandos/{id_comando}/resultado", headers=h_agente,
                        json={"exito": exito, "mensaje": mensaje})


def bitacora(cliente, h, **filtros):
    r = cliente.get("/api/panel/bitacora", headers=h, params=filtros)
    assert r.status_code == 200, r.text
    return r.json()


def test_cp22_reinicio_recorre_el_ciclo_y_queda_en_bitacora(cliente, h_tecnico):
    id_equipo, h_ag = enrolar(cliente)
    r = ordenar(cliente, h_tecnico, id_equipo, tipo="ReiniciarApagar", modo="Reiniciar")
    assert r.status_code == 201 and r.json()["estado"] == "Pendiente"
    ordenes = pendientes(cliente, h_ag)
    assert ordenes == [{"idComando": r.json()["idComando"], "tipo": "ReiniciarApagar",
                        "parametros": {"modo": "Reiniciar"}, "interrumpeUso": True, "simulado": False}]
    assert pendientes(cliente, h_ag) == []  # ya fue entregada: no se entrega dos veces
    assert informar(cliente, h_ag, ordenes[0]["idComando"]).status_code == 204
    [entrada] = bitacora(cliente, h_tecnico)
    assert entrada["estadoResultante"] == "Ejecutado" and entrada["cerrada"] is True
    assert entrada["nombreUsuario"] == "Técnico Uno" and entrada["nombreEquipo"] == "PC-PRUEBA-01"
    assert entrada["fechaOrden"] and entrada["fechaResultado"]  # todos los campos de RF14


def test_cp22b_resultado_fallido_guarda_el_motivo(cliente, h_tecnico):
    id_equipo, h_ag = enrolar(cliente)
    id_c = ordenar(cliente, h_tecnico, id_equipo, tipo="ReiniciarApagar", modo="Apagar").json()["idComando"]
    pendientes(cliente, h_ag)
    informar(cliente, h_ag, id_c, exito=False, mensaje="Acceso denegado")
    [orden] = cliente.get("/api/panel/comandos", headers=h_tecnico).json()
    assert orden["estado"] == "Fallido" and orden["motivoFallo"] == "Acceso denegado"
    assert bitacora(cliente, h_tecnico)[0]["estadoResultante"] == "Fallido"


@pytest.mark.parametrize("modo", [None, "Hibernar"])
def test_cp22c_modo_invalido_no_crea_orden(cliente, h_tecnico, modo):
    id_equipo, _ = enrolar(cliente)
    assert ordenar(cliente, h_tecnico, id_equipo, tipo="ReiniciarApagar", modo=modo).status_code == 422
    assert bitacora(cliente, h_tecnico) == []


def test_cp23_cancelar_solo_mientras_esta_pendiente(cliente, h_tecnico):
    id_equipo, h_ag = enrolar(cliente)
    id_1 = ordenar(cliente, h_tecnico, id_equipo, tipo="ReiniciarApagar", modo="Reiniciar").json()["idComando"]
    assert cliente.post(f"/api/panel/comandos/{id_1}/cancelar", headers=h_tecnico).json()["estado"] == "Cancelado"
    assert pendientes(cliente, h_ag) == []  # una orden cancelada no llega al equipo
    id_2 = ordenar(cliente, h_tecnico, id_equipo, tipo="ReiniciarApagar", modo="Reiniciar").json()["idComando"]
    pendientes(cliente, h_ag)  # pasa a Entregado
    assert cliente.post(f"/api/panel/comandos/{id_2}/cancelar", headers=h_tecnico).status_code == 422
    estados = {e["estadoResultante"] for e in bitacora(cliente, h_tecnico)}
    assert estados == {"Cancelado", "Pendiente"}  # la segunda sigue abierta (Entregado, en curso)


def test_cp24_ordenes_vencidas_expiran(cliente, contenedor, h_tecnico):
    id_equipo, h_ag = enrolar(cliente)
    ordenar(cliente, h_tecnico, id_equipo, tipo="ReiniciarApagar", modo="Reiniciar")
    assert contenedor.acciones.expirar_vencidos(ahora() + timedelta(hours=23, minutes=59)) == []
    assert len(contenedor.acciones.expirar_vencidos(ahora() + timedelta(hours=24, minutes=1))) == 1
    contenedor.bd.commit()
    assert bitacora(cliente, h_tecnico)[0]["estadoResultante"] == "Expirado"
    assert pendientes(cliente, h_ag) == []


@pytest.mark.parametrize("nombre_escrito", ["", "pc-prueba-01", "PC-PRUEBA-0", "PC-PRUEBA-01 "])
def test_cp25_formateo_sin_confirmacion_exacta_no_crea_orden(cliente, h_admin, nombre_escrito):
    id_equipo, _ = enrolar(cliente)
    r = ordenar(cliente, h_admin, id_equipo, tipo="Formatear", nombreConfirmado=nombre_escrito)
    assert r.status_code == 422
    assert bitacora(cliente, h_admin) == []


def test_cp25b_formateo_con_confirmacion_exacta_es_simulado(cliente, h_admin):
    id_equipo, h_ag = enrolar(cliente)
    r = ordenar(cliente, h_admin, id_equipo, tipo="Formatear", nombreConfirmado="PC-PRUEBA-01")
    assert r.status_code == 201 and r.json()["simulado"] is True
    assert pendientes(cliente, h_ag)[0]["simulado"] is True


def test_cp26_tecnico_no_puede_formatear_y_el_intento_queda_registrado(cliente, h_tecnico):
    """RF11 y RNF07: 403 para el Técnico; excepción 1f de CU07: el intento queda en la bitácora."""
    id_equipo, h_ag = enrolar(cliente)
    r = ordenar(cliente, h_tecnico, id_equipo, tipo="Formatear", nombreConfirmado="PC-PRUEBA-01")
    assert r.status_code == 403
    assert pendientes(cliente, h_ag) == []
    [entrada] = bitacora(cliente, h_tecnico)
    assert entrada["estadoResultante"] == "Denegado" and entrada["tipoAccion"] == "Formatear"


def test_cp27_cada_orden_genera_exactamente_una_entrada(cliente, h_tecnico):
    id_equipo, h_ag = enrolar(cliente)
    for _ in range(3):
        ordenar(cliente, h_tecnico, id_equipo, tipo="ReiniciarApagar", modo="Reiniciar")
    for orden in pendientes(cliente, h_ag):
        informar(cliente, h_ag, orden["idComando"])
    entradas = bitacora(cliente, h_tecnico)
    assert len(entradas) == 3 and all(e["cerrada"] for e in entradas)


def test_cp27b_bitacora_no_expone_edicion_ni_borrado(app):
    """RNF12: el contrato OpenAPI solo tiene GET sobre /bitacora."""
    rutas = app.openapi()["paths"]
    for ruta, operaciones in rutas.items():
        if "/bitacora" in ruta:
            assert set(operaciones) == {"get"}, ruta


def test_cp27c_un_resultado_solo_se_registra_una_vez(cliente, h_tecnico):
    id_equipo, h_ag = enrolar(cliente)
    ordenar(cliente, h_tecnico, id_equipo, tipo="ReiniciarApagar", modo="Reiniciar")
    [orden] = pendientes(cliente, h_ag)
    assert informar(cliente, h_ag, orden["idComando"]).status_code == 204
    assert informar(cliente, h_ag, orden["idComando"], exito=False).status_code == 422
    assert bitacora(cliente, h_tecnico)[0]["estadoResultante"] == "Ejecutado"


def test_cp27d_un_agente_no_puede_informar_ordenes_de_otro_equipo(cliente, h_tecnico):
    id_1, _ = enrolar(cliente, "PC-1")
    _, h_otro = enrolar(cliente, "PC-2")
    id_c = ordenar(cliente, h_tecnico, id_1, tipo="ReiniciarApagar", modo="Reiniciar").json()["idComando"]
    assert informar(cliente, h_otro, id_c).status_code == 404


@pytest.fixture
def bitacora_conocida(cliente, h_admin, h_tecnico):
    """4 órdenes: técnico→PC-A reinicio, técnico→PC-B apagado, admin→PC-A reinicio, admin→PC-B formateo."""
    a, _ = enrolar(cliente, "PC-A")
    b, _ = enrolar(cliente, "PC-B")
    ordenar(cliente, h_tecnico, a, tipo="ReiniciarApagar", modo="Reiniciar")
    ordenar(cliente, h_tecnico, b, tipo="ReiniciarApagar", modo="Apagar")
    ordenar(cliente, h_admin, a, tipo="ReiniciarApagar", modo="Reiniciar")
    ordenar(cliente, h_admin, b, tipo="Formatear", nombreConfirmado="PC-B")
    ids_usuario = {u["nombre"]: u["idUsuario"] for u in cliente.get("/api/panel/usuarios", headers=h_admin).json()}
    return {"A": a, "B": b, "tec": ids_usuario["Técnico Uno"], "adm": ids_usuario["Administrador inicial"]}


@pytest.mark.parametrize("filtros, esperado", [
    ({}, 4),
    ({"equipo": "A"}, 2),
    ({"usuario": "tec"}, 2),
    ({"tipo": "Formatear"}, 1),
    ({"equipo": "B", "usuario": "adm"}, 1),
    ({"equipo": "A", "tipo": "Formatear"}, 0),
])
def test_cp28_filtros_de_la_bitacora(cliente, h_admin, bitacora_conocida, filtros, esperado):
    parametros = {k: bitacora_conocida[v] if v in bitacora_conocida else v for k, v in filtros.items()}
    assert len(bitacora(cliente, h_admin, **parametros)) == esperado


def test_cp28b_filtro_por_rango_de_fechas(cliente, h_admin, bitacora_conocida):
    ahora_utc = datetime.now(timezone.utc)
    assert len(bitacora(cliente, h_admin, desde=(ahora_utc - timedelta(hours=1)).isoformat())) == 4
    assert len(bitacora(cliente, h_admin, desde=(ahora_utc + timedelta(hours=1)).isoformat())) == 0
    r = cliente.get("/api/panel/bitacora", headers=h_admin, params={
        "desde": ahora_utc.isoformat(), "hasta": (ahora_utc - timedelta(days=1)).isoformat()})
    assert r.status_code == 422  # «desde» posterior a «hasta»
