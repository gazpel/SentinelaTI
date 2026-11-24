"""Contratos de persistencia (L4, cambio C4: patrón Repositorio).

El dominio y los servicios dependen solo de estas interfaces; las
implementaciones con SQLAlchemy están en app/infraestructura/repositorios_sql.py
(inversión de dependencias). Solo se declaran las operaciones que usa el L5.
"""
from abc import ABC, abstractmethod
from datetime import datetime

from .acciones import Comando
from .auditoria import EntradaBitacora, FiltroBitacora
from .enumeraciones import EstadoComando, EstadoEquipo, Metrica
from .monitoreo import Alerta, ConfiguracionUmbrales, Equipo, Lectura, Umbral
from .usuarios import Usuario


class UsuarioRepository(ABC):
    @abstractmethod
    def obtener_por_correo(self, correo: str) -> Usuario | None: ...
    @abstractmethod
    def obtener_por_id(self, id_usuario: str) -> Usuario | None: ...
    @abstractmethod
    def listar(self) -> list[Usuario]: ...
    @abstractmethod
    def guardar(self, u: Usuario) -> None: ...


class EquipoRepository(ABC):
    @abstractmethod
    def obtener_por_id(self, id_equipo: str) -> Equipo | None: ...
    @abstractmethod
    def buscar_por_numero_serie(self, serie: str) -> Equipo | None: ...
    @abstractmethod
    def buscar_por_token(self, token_plano: str) -> Equipo | None: ...
    @abstractmethod
    def listar_con_filtros(self, estado: EstadoEquipo | None, texto: str | None,
                           pagina: int, tamano: int) -> tuple[list[Equipo], int]:
        """Equipos ordenados por severidad y nombre, paginados (D6). Devuelve (página, total)."""
    @abstractmethod
    def contar_por_estado(self) -> dict[EstadoEquipo, int]: ...
    @abstractmethod
    def listar_sin_reporte_desde(self, limite: datetime) -> list[Equipo]: ...
    @abstractmethod
    def guardar(self, e: Equipo) -> None: ...


class LecturaRepository(ABC):
    @abstractmethod
    def existe(self, e: Equipo, marca_tiempo: datetime) -> bool: ...
    @abstractmethod
    def agregar(self, e: Equipo, l: Lectura) -> None: ...
    @abstractmethod
    def historial(self, e: Equipo, desde: datetime, hasta: datetime) -> list[Lectura]: ...
    @abstractmethod
    def ultima(self, e: Equipo) -> Lectura | None: ...


class AlertaRepository(ABC):
    @abstractmethod
    def abierta_de(self, e: Equipo, m: Metrica | None) -> Alerta | None: ...
    @abstractmethod
    def listar_abiertas(self, pagina: int, tamano: int) -> tuple[list[Alerta], int]: ...
    @abstractmethod
    def abiertas_de_equipo(self, e: Equipo) -> list[Alerta]: ...
    @abstractmethod
    def contar_abiertas(self) -> int: ...
    @abstractmethod
    def guardar(self, a: Alerta) -> None: ...


class ConfiguracionRepository(ABC):
    @abstractmethod
    def obtener(self) -> ConfiguracionUmbrales: ...
    @abstractmethod
    def guardar(self, u: Umbral) -> None: ...


class ComandoRepository(ABC):
    @abstractmethod
    def guardar(self, c: Comando) -> None: ...
    @abstractmethod
    def obtener_por_id(self, id_comando: str) -> Comando | None: ...
    @abstractmethod
    def pendientes_de(self, e: Equipo) -> list[Comando]: ...
    @abstractmethod
    def vigentes(self) -> list[Comando]:
        """Órdenes Pendientes o Entregadas, candidatas a expirar."""
    @abstractmethod
    def listar(self, equipo: Equipo | None, estado: EstadoComando | None, limite: int) -> list[Comando]: ...


class BitacoraRepository(ABC):
    """Sin operaciones de edición ni de borrado (RNF12): ``cerrar`` solo completa una entrada abierta."""

    @abstractmethod
    def agregar(self, en: EntradaBitacora) -> None: ...
    @abstractmethod
    def de_comando(self, id_comando: str) -> EntradaBitacora | None: ...
    @abstractmethod
    def cerrar(self, en: EntradaBitacora) -> None: ...
    @abstractmethod
    def buscar(self, f: FiltroBitacora, limite: int) -> list[EntradaBitacora]: ...
