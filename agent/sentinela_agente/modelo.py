"""Estructuras de datos que el agente intercambia con la API (contrato IAgenteAPI)."""
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum


@dataclass
class UsoDisco:
    unidad: str
    uso_porcentaje: float


@dataclass
class Lectura:
    """Exactamente los campos de RF02 (RNF05: no se recolecta nada más)."""

    marca_tiempo: datetime
    uso_cpu: float
    uso_ram: float
    discos: list[UsoDisco]
    temperatura_cpu: float | None  # None = «no disponible», nunca 0
    horas_encendido: float

    def a_json(self) -> dict:
        return {
            "marcaTiempo": self.marca_tiempo.isoformat(),
            "usoCpu": round(self.uso_cpu, 1),
            "usoRam": round(self.uso_ram, 1),
            "discos": [{"unidad": d.unidad, "usoPorcentaje": round(d.uso_porcentaje, 1)} for d in self.discos],
            "temperaturaCpu": None if self.temperatura_cpu is None else round(self.temperatura_cpu, 1),
            "horasEncendido": round(self.horas_encendido, 2),
        }

    @classmethod
    def desde_json(cls, d: dict) -> "Lectura":
        return cls(
            marca_tiempo=datetime.fromisoformat(d["marcaTiempo"]), uso_cpu=d["usoCpu"], uso_ram=d["usoRam"],
            discos=[UsoDisco(x["unidad"], x["usoPorcentaje"]) for x in d["discos"]],
            temperatura_cpu=d["temperaturaCpu"], horas_encendido=d["horasEncendido"])


@dataclass
class DatosEquipo:
    nombre: str
    numero_serie: str
    modelo: str | None = None
    sistema_operativo: str | None = None
    direccion_ip: str | None = None
    ultimo_usuario: str | None = None

    def a_json(self) -> dict:
        d = asdict(self)
        return {"nombre": d["nombre"], "numeroSerie": d["numero_serie"], "modelo": d["modelo"],
                "sistemaOperativo": d["sistema_operativo"], "direccionIp": d["direccion_ip"],
                "ultimoUsuario": d["ultimo_usuario"]}


class TipoAccion(str, Enum):
    REINICIAR_APAGAR = "ReiniciarApagar"
    INSTALAR_APP = "InstalarApp"
    ACTUALIZAR_SO = "ActualizarSO"
    FORMATEAR = "Formatear"
    ESCRITORIO_REMOTO = "EscritorioRemoto"


@dataclass(frozen=True)
class OrdenComando:
    """DTO recibido del servidor (L4, C2)."""

    id_comando: str
    tipo: TipoAccion
    parametros: dict[str, str] = field(default_factory=dict)
    interrumpe_uso: bool = False
    simulado: bool = False

    @classmethod
    def desde_json(cls, d: dict) -> "OrdenComando":
        return cls(id_comando=d["idComando"], tipo=TipoAccion(d["tipo"]), parametros=d.get("parametros", {}),
                   interrumpe_uso=d.get("interrumpeUso", False), simulado=d.get("simulado", False))


@dataclass(frozen=True)
class ResultadoEjecucion:
    exito: bool
    mensaje: str | None = None


class DesenlaceAviso(str, Enum):
    EJECUTAR_AHORA = "EjecutarAhora"
    CUENTA_TERMINADA = "CuentaTerminada"
    POSPUESTO = "Pospuesto"
    SIN_SESION_ABIERTA = "SinSesionAbierta"
