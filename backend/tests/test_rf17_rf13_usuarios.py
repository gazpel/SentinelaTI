"""RF17 (inicio de sesión), RF13 (usuarios) y RNF07 (control de acceso). Casos CP-01 a CP-08."""
import pytest

from conftest import ADMIN, iniciar_sesion

RUTAS_PANEL = ["/api/panel/equipos", "/api/panel/alertas", "/api/panel/comandos", "/api/panel/bitacora",
               "/api/panel/umbrales", "/api/panel/usuarios", "/api/panel/sesion"]


def test_cp01_inicio_de_sesion_valido_entrega_token_y_permisos(cliente):
    r = cliente.post("/api/panel/sesion", json={"correo": ADMIN[0], "clave": ADMIN[1]})
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["token"] and cuerpo["usuario"]["rol"] == "Administrador"
    assert "Formatear" in cuerpo["usuario"]["permisos"]


def test_cp02_credenciales_incorrectas_mensaje_generico(cliente):
    clave_mala = cliente.post("/api/panel/sesion", json={"correo": ADMIN[0], "clave": "otra"})
    correo_malo = cliente.post("/api/panel/sesion", json={"correo": "nadie@prueba.cl", "clave": "otra"})
    assert clave_mala.status_code == correo_malo.status_code == 401
    assert clave_mala.json() == correo_malo.json()  # no revela qué dato falló (CU03 3b)


@pytest.mark.parametrize("ruta", RUTAS_PANEL)
def test_cp03_endpoints_del_panel_sin_sesion_responden_401(cliente, ruta):
    assert cliente.get(ruta).status_code == 401
    assert cliente.get(ruta, headers={"Authorization": "Bearer token.falso.x"}).status_code == 401


def test_cp04_bloqueo_tras_cinco_intentos_fallidos_valor_limite(cliente):
    for _ in range(4):  # 4 fallos: todavía no se bloquea (valor límite inferior)
        assert cliente.post("/api/panel/sesion", json={"correo": ADMIN[0], "clave": "x"}).status_code == 401
    assert cliente.post("/api/panel/sesion", json={"correo": ADMIN[0], "clave": ADMIN[1]}).status_code == 200
    for _ in range(5):  # el 5.º fallo consecutivo bloquea
        cliente.post("/api/panel/sesion", json={"correo": ADMIN[0], "clave": "x"})
    r = cliente.post("/api/panel/sesion", json={"correo": ADMIN[0], "clave": ADMIN[1]})
    assert r.status_code == 423  # bloqueada aunque la clave sea correcta


def test_cp05_usuario_creado_ingresa_con_permisos_de_su_rol(cliente, h_tecnico):
    yo = cliente.get("/api/panel/sesion", headers=h_tecnico).json()
    assert yo["rol"] == "Tecnico"
    assert set(yo["permisos"]) == {"ConsultarParque", "OrdenarAccion", "ConsultarBitacora"}


def test_cp06_usuario_desactivado_no_ingresa_y_pierde_su_sesion(cliente, h_admin, h_tecnico):
    id_tec = cliente.get("/api/panel/sesion", headers=h_tecnico).json()["idUsuario"]
    assert cliente.post(f"/api/panel/usuarios/{id_tec}/desactivar", headers=h_admin).status_code == 200
    assert cliente.get("/api/panel/equipos", headers=h_tecnico).status_code == 401
    assert cliente.post("/api/panel/sesion", json={"correo": "tec@prueba.cl", "clave": "Tecnico.123"}).status_code == 401


def test_cp07_funciones_de_administrador_con_sesion_de_tecnico_responden_403(cliente, h_tecnico):
    """RNF07: gestión de usuarios y umbrales son exclusivas del Administrador."""
    assert cliente.get("/api/panel/usuarios", headers=h_tecnico).status_code == 403
    assert cliente.post("/api/panel/usuarios", headers=h_tecnico, json={
        "nombre": "X", "correo": "x@prueba.cl", "rol": "Administrador", "clave": "12345678"}).status_code == 403
    assert cliente.put("/api/panel/umbrales/CPU", headers=h_tecnico,
                       json={"advertencia": 50, "critico": 60}).status_code == 403


def test_cp08_editar_rol_cambia_los_permisos(cliente, h_admin, h_tecnico):
    id_tec = cliente.get("/api/panel/sesion", headers=h_tecnico).json()["idUsuario"]
    r = cliente.put(f"/api/panel/usuarios/{id_tec}", headers=h_admin, json={"nombre": "Técnico Uno", "rol": "Administrador"})
    assert r.status_code == 200 and r.json()["rol"] == "Administrador"
    assert cliente.get("/api/panel/usuarios", headers=h_tecnico).status_code == 200


@pytest.mark.parametrize("clave, esperado", [("1234567", 422), ("12345678", 201)])  # valor límite: 8 caracteres
def test_cp08b_largo_minimo_de_contrasena(cliente, h_admin, clave, esperado):
    r = cliente.post("/api/panel/usuarios", headers=h_admin,
                     json={"nombre": "Nuevo", "correo": f"n{len(clave)}@prueba.cl", "rol": "Tecnico", "clave": clave})
    assert r.status_code == esperado


def test_cp08c_correo_duplicado_se_rechaza(cliente, h_admin):
    datos = {"nombre": "Dup", "correo": "dup@prueba.cl", "rol": "Tecnico", "clave": "Clave.1234"}
    assert cliente.post("/api/panel/usuarios", headers=h_admin, json=datos).status_code == 201
    assert cliente.post("/api/panel/usuarios", headers=h_admin, json={**datos, "correo": "DUP@prueba.cl"}).status_code == 422


def test_admin_no_puede_desactivarse_a_si_mismo(cliente, h_admin):
    yo = cliente.get("/api/panel/sesion", headers=h_admin).json()["idUsuario"]
    assert cliente.post(f"/api/panel/usuarios/{yo}/desactivar", headers=h_admin).status_code == 422
    assert iniciar_sesion(cliente, *ADMIN)
