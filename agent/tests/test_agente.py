"""Pruebas del agente: RF02 (intervalo), RNF04 (cola local), RF08 (ejecutores) y CU02 3a (token rechazado).
Casos CP-29 a CP-33. No requieren el servidor: la API se simula con httpx.MockTransport."""
import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from sentinela_agente.agente import AgenteSentinela
from sentinela_agente.cliente_api import ClienteAPI, ErrorRed
from sentinela_agente.cola_local import ColaLocalLecturas
from sentinela_agente.config import ConfiguracionAgente, ConfiguracionInvalida, validar_intervalo_reporte
from sentinela_agente.ejecutores import EjecutorReinicioApagado, EjecutorSimulado
from sentinela_agente.modelo import DatosEquipo, Lectura, OrdenComando, TipoAccion, UsoDisco
from sentinela_agente.notificador import NotificadorUsuario


# --------------------------------------------------------------------------- CP-29 intervalo (RF02)
@pytest.mark.parametrize("minutos, valido", [
    (0, False),    # P1 inválida: bajo el mínimo (límite)
    (1, True),     # P2 válida: mínimo
    (5, True),     # P2 válida: valor por defecto
    (60, True),    # P2 válida: máximo
    (61, False),   # P3 inválida: sobre el máximo (límite)
    (-5, False),   # P1 inválida: negativo
    ("5", False),  # P4 inválida: no es un número entero
    (2.5, False),  # P4 inválida: fracción de minuto
])
def test_cp29_particiones_del_intervalo_de_reporte(minutos, valido):
    if valido:
        assert validar_intervalo_reporte(minutos) == minutos
    else:
        with pytest.raises(ConfiguracionInvalida):
            validar_intervalo_reporte(minutos)


# --------------------------------------------------------------------------- utilidades
class RecolectorFalso:
    def __init__(self):
        self.t = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)

    def componer_lectura(self):
        self.t += timedelta(minutes=5)
        return Lectura(self.t, 10, 20, [UsoDisco("C:", 30)], None, 1)


class InventarioFalso:
    def leer_hardware(self):
        return DatosEquipo(nombre="VM-PRUEBA", numero_serie="S-1")


class ServidorFalso:
    """Simula IAgenteAPI. ``en_linea=False`` simula un corte de red."""

    def __init__(self):
        self.en_linea = True
        self.lecturas: list[str] = []
        self.resultados: dict[str, dict] = {}
        self.ordenes: list[dict] = []
        self.token_valido = "tok-1"

    def __call__(self, req: httpx.Request) -> httpx.Response:
        if not self.en_linea:
            raise httpx.ConnectError("sin red", request=req)
        if req.url.path == "/api/agente/enrolamiento":
            return httpx.Response(201, json={"idEquipo": "e1", "token": self.token_valido, "intervaloReporteMin": 5})
        if req.headers.get("Authorization") != f"Bearer {self.token_valido}":
            return httpx.Response(401, json={"detail": "token"})
        if req.url.path == "/api/agente/lecturas":
            marca = json.loads(req.content)["marcaTiempo"]
            duplicada = marca in self.lecturas
            if not duplicada:
                self.lecturas.append(marca)
            return httpx.Response(200, json={"registrada": not duplicada, "duplicada": duplicada})
        if req.url.path == "/api/agente/comandos/pendientes":
            ordenes, self.ordenes = self.ordenes, []
            return httpx.Response(200, json=ordenes)
        if req.url.path.endswith("/resultado"):
            self.resultados[req.url.path.split("/")[-2]] = json.loads(req.content)
            return httpx.Response(204)
        return httpx.Response(404)


@pytest.fixture
def servidor():
    return ServidorFalso()


@pytest.fixture
def agente(tmp_path, servidor):
    cfg = ConfiguracionAgente(url_servidor="http://servidor", codigo_enrolamiento="COD", carpeta_datos=tmp_path,
                              segundos_aviso=0)
    cliente = ClienteAPI(cfg.url_servidor, transporte=httpx.MockTransport(servidor))
    a = AgenteSentinela(cfg, cliente=cliente, recolector=RecolectorFalso(), inventario=InventarioFalso(),
                        notificador=NotificadorUsuario(0))
    a.enrolar("COD")
    yield a
    a.cola.cerrar()


# --------------------------------------------------------------------------- CP-30 cola local (RNF04)
def test_cp30_sin_conexion_encola_y_al_reconectar_reenvia_en_orden_sin_duplicados(agente, servidor):
    servidor.en_linea = False
    for _ in range(24):  # 2 horas sin red con lecturas cada 5 minutos (criterio de RNF04)
        agente.ciclo_reporte()
    assert agente.cola.cantidad() == 24 and servidor.lecturas == []
    servidor.en_linea = True
    agente.ciclo_reporte()
    assert agente.cola.cantidad() == 0
    assert len(servidor.lecturas) == 25 == len(set(servidor.lecturas))
    assert servidor.lecturas == sorted(servidor.lecturas)  # orden cronológico, con su marca original


def test_cp30b_la_cola_descarta_lo_anterior_a_la_retencion(tmp_path):
    cola = ColaLocalLecturas(tmp_path / "cola.sqlite3", retencion_horas=72)
    ahora = datetime.now(timezone.utc)
    cola.encolar(Lectura(ahora - timedelta(hours=73), 1, 1, [UsoDisco("C:", 1)], None, 1))
    cola.encolar(Lectura(ahora - timedelta(hours=71), 1, 1, [UsoDisco("C:", 1)], None, 1))
    assert cola.cantidad() == 1
    cola.cerrar()


def test_cp30c_la_cola_sobrevive_a_un_reinicio_del_agente(tmp_path):
    ruta = tmp_path / "cola.sqlite3"
    cola = ColaLocalLecturas(ruta)
    cola.encolar(Lectura(datetime.now(timezone.utc), 1, 1, [UsoDisco("C:", 1)], None, 1))
    cola.cerrar()
    assert ColaLocalLecturas(ruta).cantidad() == 1


# --------------------------------------------------------------------------- CP-31 token rechazado (CU02 3a)
def test_cp31_token_revocado_provoca_reenrolamiento(agente, servidor):
    servidor.token_valido = "tok-2"  # el servidor revocó el token anterior
    agente.ciclo_reporte()           # recibe 401 → se reenrola → la lectura queda en cola
    assert agente.almacen.leer() == "tok-2"
    agente.ciclo_reporte()
    assert len(servidor.lecturas) == 2 and agente.cola.cantidad() == 0


# --------------------------------------------------------------------------- CP-32 ejecución de órdenes (RF08)
def test_cp32_orden_de_reinicio_en_modo_seguro_informa_resultado(agente, servidor):
    servidor.ordenes = [{"idComando": "c1", "tipo": "ReiniciarApagar", "parametros": {"modo": "Reiniciar"},
                         "interrumpeUso": True, "simulado": False}]
    for hilo in agente.ciclo_comandos():
        hilo.join()
    assert servidor.resultados["c1"]["exito"] is True
    assert "Modo seguro" in servidor.resultados["c1"]["mensaje"]


@pytest.mark.parametrize("modo, bandera", [("Reiniciar", "/r"), ("Apagar", "/s")])
def test_cp32b_reinicio_real_llama_a_shutdown(monkeypatch, modo, bandera):
    llamadas = []
    monkeypatch.setattr("sentinela_agente.ejecutores.platform.system", lambda: "Windows")
    ejecutor = EjecutorReinicioApagado(acciones_reales=True, ejecutar_proceso=lambda args, **kw: (
        llamadas.append(args) or type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()))
    r = ejecutor.ejecutar(OrdenComando("c", TipoAccion.REINICIAR_APAGAR, {"modo": modo}, True))
    assert r.exito and llamadas[0][:2] == ["shutdown", bandera]


def test_cp32c_fallo_de_shutdown_se_informa_como_fallido(monkeypatch):
    monkeypatch.setattr("sentinela_agente.ejecutores.platform.system", lambda: "Windows")
    ejecutor = EjecutorReinicioApagado(True, lambda args, **kw: type("R", (), {"returncode": 5, "stdout": "", "stderr": "Acceso denegado"})())
    r = ejecutor.ejecutar(OrdenComando("c", TipoAccion.REINICIAR_APAGAR, {"modo": "Reiniciar"}, True))
    assert not r.exito and r.mensaje == "Acceso denegado"


def test_cp33_seleccion_de_ejecutor_estrategia(agente):
    assert isinstance(agente.seleccionar_ejecutor(TipoAccion.REINICIAR_APAGAR), EjecutorReinicioApagado)
    assert isinstance(agente.seleccionar_ejecutor(TipoAccion.FORMATEAR), EjecutorSimulado)


def test_cp33b_orden_sin_ejecutor_se_informa_como_fallida(agente, servidor):
    r = agente.ejecutar_comando(OrdenComando("c9", TipoAccion.INSTALAR_APP, {}, False))
    assert not r.exito and servidor.resultados["c9"]["exito"] is False


def test_cliente_convierte_errores_de_transporte(servidor):
    servidor.en_linea = False
    cliente = ClienteAPI("http://servidor", "tok-1", transporte=httpx.MockTransport(servidor))
    with pytest.raises(ErrorRed):
        cliente.get_comandos_pendientes()


# --------------------------------------------------------------------------- hallazgos de la prueba del prototipo
@pytest.mark.parametrize("serie, valida", [
    ("PF3ABCDE", True), ("System Serial Number", False), ("To Be Filled By O.E.M.", False),
    ("Default string", False), ("  0 ", False), (None, False), ("", False),
])
def test_series_genericas_de_fabrica_no_identifican_al_equipo(serie, valida):
    """Una serie genérica haría que equipos distintos se fusionen en uno al enrolarse (RF01)."""
    from sentinela_agente.recolectores import es_serie_valida
    assert es_serie_valida(serie) is valida


@pytest.mark.parametrize("explicito, esperado_seg", [(False, 300), (True, 60)])
def test_intervalo_configurado_prevalece_sobre_el_del_servidor(tmp_path, servidor, explicito, esperado_seg):
    cfg = ConfiguracionAgente(url_servidor="http://servidor", codigo_enrolamiento="COD", carpeta_datos=tmp_path,
                              intervalo_reporte_min=1, intervalo_explicito=explicito, segundos_aviso=0)
    a = AgenteSentinela(cfg, cliente=ClienteAPI(cfg.url_servidor, transporte=httpx.MockTransport(servidor)),
                        recolector=RecolectorFalso(), inventario=InventarioFalso(), notificador=NotificadorUsuario(0))
    a.enrolar("COD")
    assert a.intervalo_reporte_seg == esperado_seg
    a.cola.cerrar()
