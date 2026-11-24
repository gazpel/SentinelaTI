"""ServicioEnrolamiento (L4) — RF01, CU01, RNF01 (decisión D1: token propio por agente)."""
import hmac
from dataclasses import dataclass

from app.aplicacion.errores import DatosInvalidos, NoAutenticado
from app.dominio.monitoreo import Equipo
from app.dominio.repositorios import EquipoRepository
from app.infraestructura import seguridad


@dataclass(frozen=True)
class DatosEquipo:
    """Datos que el agente informa al enrolarse (subconjunto de RF03)."""

    nombre: str
    numero_serie: str
    modelo: str | None = None
    sistema_operativo: str | None = None
    direccion_ip: str | None = None
    ultimo_usuario: str | None = None


class ServicioEnrolamiento:
    def __init__(self, equipos: EquipoRepository, codigo_vigente: str):
        self.equipos = equipos
        self.codigo_vigente = codigo_vigente

    def validar_codigo(self, codigo: str) -> bool:
        return hmac.compare_digest(codigo.encode(), self.codigo_vigente.encode())

    def enrolar(self, codigo: str, datos: DatosEquipo) -> tuple[Equipo, str]:
        """Devuelve el equipo y el token en texto plano (solo se muestra esta vez)."""
        if not self.validar_codigo(codigo):
            raise NoAutenticado("Código de enrolamiento inválido.")
        if not datos.numero_serie.strip() or not datos.nombre.strip():
            raise DatosInvalidos("El equipo debe informar nombre y número de serie.")
        equipo = self.buscar_por_numero_serie(datos.numero_serie)
        if equipo is None:
            equipo = Equipo(numero_serie=datos.numero_serie, tokens=[])
        # Un reenrolamiento (p. ej. el agente se reinstaló) actualiza los datos y
        # revoca el token anterior en vez de duplicar el equipo.
        equipo.nombre = datos.nombre
        equipo.modelo = datos.modelo
        equipo.sistema_operativo = datos.sistema_operativo
        equipo.direccion_ip = datos.direccion_ip
        equipo.ultimo_usuario = datos.ultimo_usuario
        token_plano = seguridad.nuevo_token_agente()
        equipo.emitir_token(token_plano)
        self.equipos.guardar(equipo)
        return equipo, token_plano

    def buscar_por_numero_serie(self, serie: str) -> Equipo | None:
        return self.equipos.buscar_por_numero_serie(serie)

    def autenticar_agente(self, token: str | None) -> Equipo:
        equipo = self.equipos.buscar_por_token(token) if token else None
        if equipo is None:
            raise NoAutenticado("Token de agente inválido o revocado.")
        return equipo
