"""ClienteAPI (L4) — única puerta de salida del agente hacia el servidor (HTTPS saliente, D1/D2)."""
import httpx

from .modelo import DatosEquipo, Lectura, OrdenComando, ResultadoEjecucion


class ErrorRed(Exception):
    """El servidor no respondió: la lectura se guarda en la cola local (excepción 2a de CU02)."""


class TokenRechazado(Exception):
    """401: el token fue revocado o no es válido → hay que volver a enrolar (excepción 3a de CU02)."""


class ErrorServidor(Exception):
    """El servidor rechazó la petición por otro motivo (4xx/5xx)."""


class ClienteAPI:
    def __init__(self, url_servidor: str, token: str | None = None, timeout: float = 15.0,
                 transporte: httpx.BaseTransport | None = None):
        self.token = token
        self._http = httpx.Client(base_url=url_servidor.rstrip("/"), timeout=timeout, transport=transporte)

    def post_enrolamiento(self, codigo: str, datos: DatosEquipo) -> tuple[str, int]:
        """Devuelve (token, intervalo de reporte en minutos que indica el servidor)."""
        r = self._enviar("POST", "/api/agente/enrolamiento", json={"codigo": codigo, **datos.a_json()},
                         autenticado=False)
        cuerpo = r.json()
        self.token = cuerpo["token"]
        return cuerpo["token"], cuerpo["intervaloReporteMin"]

    def post_lectura(self, l: Lectura) -> bool:
        self._enviar("POST", "/api/agente/lecturas", json=l.a_json())
        return True

    def get_comandos_pendientes(self) -> list[OrdenComando]:
        r = self._enviar("GET", "/api/agente/comandos/pendientes")
        return [OrdenComando.desde_json(o) for o in r.json()]

    def post_resultado(self, id_comando: str, r: ResultadoEjecucion) -> bool:
        self._enviar("POST", f"/api/agente/comandos/{id_comando}/resultado",
                     json={"exito": r.exito, "mensaje": r.mensaje})
        return True

    def _enviar(self, metodo: str, ruta: str, json: dict | None = None, autenticado: bool = True) -> httpx.Response:
        cabeceras = {"Authorization": f"Bearer {self.token}"} if autenticado and self.token else {}
        try:
            respuesta = self._http.request(metodo, ruta, json=json, headers=cabeceras)
        except httpx.TransportError as error:
            raise ErrorRed(str(error)) from error
        if respuesta.status_code == 401:
            raise TokenRechazado(respuesta.text)
        if respuesta.status_code >= 400:
            raise ErrorServidor(f"{respuesta.status_code}: {respuesta.text}")
        return respuesta

    def cerrar(self) -> None:
        self._http.close()
