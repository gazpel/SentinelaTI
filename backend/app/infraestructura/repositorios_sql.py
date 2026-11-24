"""Implementaciones SQLAlchemy de los contratos de persistencia (L4: *RepositoryPg).

Se renombraron a *RepositorySql porque la misma implementación sirve para
PostgreSQL (producción) y SQLite (desarrollo y pruebas).
"""
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.dominio.acciones import Comando
from app.dominio.auditoria import EntradaBitacora, FiltroBitacora
from app.dominio.enumeraciones import EstadoComando, EstadoEquipo, Metrica
from app.dominio.monitoreo import (
    UMBRALES_POR_DEFECTO, Alerta, ConfiguracionUmbrales, Equipo, Lectura, TokenAgente, Umbral, hash_token)
from app.dominio.repositorios import (
    AlertaRepository, BitacoraRepository, ComandoRepository, ConfiguracionRepository,
    EquipoRepository, LecturaRepository, UsuarioRepository)
from app.dominio.usuarios import Usuario


class UsuarioRepositorySql(UsuarioRepository):
    def __init__(self, s: Session):
        self.s = s

    def obtener_por_correo(self, correo: str) -> Usuario | None:
        return self.s.scalar(select(Usuario).where(func.lower(Usuario.correo) == correo.strip().lower()))

    def obtener_por_id(self, id_usuario: str) -> Usuario | None:
        return self.s.get(Usuario, id_usuario)

    def listar(self) -> list[Usuario]:
        return list(self.s.scalars(select(Usuario).order_by(Usuario.nombre)))

    def guardar(self, u: Usuario) -> None:
        self.s.add(u)
        self.s.flush()


class EquipoRepositorySql(EquipoRepository):
    def __init__(self, s: Session):
        self.s = s

    def obtener_por_id(self, id_equipo: str) -> Equipo | None:
        return self.s.get(Equipo, id_equipo)

    def buscar_por_numero_serie(self, serie: str) -> Equipo | None:
        return self.s.scalar(select(Equipo).where(Equipo.numero_serie == serie))

    def buscar_por_token(self, token_plano: str) -> Equipo | None:
        consulta = (select(Equipo).join(TokenAgente)
                    .where(TokenAgente.valor == hash_token(token_plano), TokenAgente.revocado.is_(False)))
        return self.s.scalar(consulta)

    def listar_con_filtros(self, estado, texto, pagina, tamano):
        consulta = select(Equipo)
        if estado is not None:
            consulta = consulta.where(Equipo.estado == estado)
        if texto:
            patron = f"%{texto.strip().lower()}%"
            consulta = consulta.where(or_(
                func.lower(Equipo.nombre).like(patron),
                func.lower(Equipo.direccion_ip).like(patron),
                func.lower(Equipo.ultimo_usuario).like(patron),
            ))
        total = self.s.scalar(select(func.count()).select_from(consulta.subquery()))
        pagina_equipos = self.s.scalars(
            consulta.order_by(Equipo.severidad, Equipo.nombre)
            .offset((pagina - 1) * tamano).limit(tamano))
        return list(pagina_equipos), total

    def contar_por_estado(self) -> dict[EstadoEquipo, int]:
        conteo = {estado: 0 for estado in EstadoEquipo}
        for estado, cantidad in self.s.execute(select(Equipo.estado, func.count()).group_by(Equipo.estado)):
            conteo[EstadoEquipo(estado)] = cantidad
        return conteo

    def listar_sin_reporte_desde(self, limite: datetime) -> list[Equipo]:
        return list(self.s.scalars(select(Equipo).where(
            Equipo.estado != EstadoEquipo.DESCONECTADO,
            or_(Equipo.fecha_ultimo_reporte < limite,
                Equipo.fecha_ultimo_reporte.is_(None) & (Equipo.fecha_enrolamiento < limite)))))

    def guardar(self, e: Equipo) -> None:
        self.s.add(e)
        self.s.flush()


class LecturaRepositorySql(LecturaRepository):
    def __init__(self, s: Session):
        self.s = s

    def existe(self, e: Equipo, marca_tiempo: datetime) -> bool:
        return self.s.scalar(select(func.count()).select_from(Lectura).where(
            Lectura.equipo_id == e.id_equipo, Lectura.marca_tiempo == marca_tiempo)) > 0

    def agregar(self, e: Equipo, l: Lectura) -> None:
        l.equipo_id = e.id_equipo
        self.s.add(l)
        self.s.flush()

    def historial(self, e: Equipo, desde: datetime, hasta: datetime) -> list[Lectura]:
        return list(self.s.scalars(select(Lectura).where(
            Lectura.equipo_id == e.id_equipo,
            Lectura.marca_tiempo >= desde, Lectura.marca_tiempo <= hasta,
        ).order_by(Lectura.marca_tiempo)))

    def ultima(self, e: Equipo) -> Lectura | None:
        return self.s.scalar(select(Lectura).where(Lectura.equipo_id == e.id_equipo)
                             .order_by(Lectura.marca_tiempo.desc()).limit(1))


class AlertaRepositorySql(AlertaRepository):
    def __init__(self, s: Session):
        self.s = s

    def abierta_de(self, e: Equipo, m: Metrica | None) -> Alerta | None:
        condicion_metrica = Alerta.metrica.is_(None) if m is None else Alerta.metrica == m
        return self.s.scalar(select(Alerta).where(
            Alerta.equipo_id == e.id_equipo, condicion_metrica, Alerta.fecha_cierre.is_(None)))

    def listar_abiertas(self, pagina: int, tamano: int):
        consulta = select(Alerta).where(Alerta.fecha_cierre.is_(None))
        total = self.s.scalar(select(func.count()).select_from(consulta.subquery()))
        filas = self.s.scalars(consulta.order_by(Alerta.fecha_apertura.desc())
                               .offset((pagina - 1) * tamano).limit(tamano))
        return list(filas), total

    def abiertas_de_equipo(self, e: Equipo) -> list[Alerta]:
        return list(self.s.scalars(select(Alerta).where(
            Alerta.equipo_id == e.id_equipo, Alerta.fecha_cierre.is_(None))))

    def contar_abiertas(self) -> int:
        return self.s.scalar(select(func.count()).select_from(Alerta).where(Alerta.fecha_cierre.is_(None)))

    def guardar(self, a: Alerta) -> None:
        self.s.add(a)
        self.s.flush()


class ConfiguracionRepositorySql(ConfiguracionRepository):
    def __init__(self, s: Session):
        self.s = s

    def obtener(self) -> ConfiguracionUmbrales:
        umbrales = {u.metrica: u for u in self.s.scalars(select(Umbral))}
        for metrica, (advertencia, critico) in UMBRALES_POR_DEFECTO.items():
            if metrica not in umbrales:  # primera ejecución: se crean los valores por defecto
                umbral = Umbral(metrica=metrica, valor_advertencia=advertencia, valor_critico=critico)
                self.s.add(umbral)
                umbrales[metrica] = umbral
        self.s.flush()
        return ConfiguracionUmbrales(list(umbrales.values()))

    def guardar(self, u: Umbral) -> None:
        self.s.add(u)
        self.s.flush()


class ComandoRepositorySql(ComandoRepository):
    def __init__(self, s: Session):
        self.s = s

    def guardar(self, c: Comando) -> None:
        self.s.add(c)
        self.s.flush()

    def obtener_por_id(self, id_comando: str) -> Comando | None:
        return self.s.get(Comando, id_comando)

    def pendientes_de(self, e: Equipo) -> list[Comando]:
        return list(self.s.scalars(select(Comando).where(
            Comando.equipo_id == e.id_equipo, Comando.estado == EstadoComando.PENDIENTE,
        ).order_by(Comando.fecha_orden)))

    def vigentes(self) -> list[Comando]:
        return list(self.s.scalars(select(Comando).where(
            Comando.estado.in_([EstadoComando.PENDIENTE, EstadoComando.ENTREGADO]))))

    def listar(self, equipo, estado, limite):
        consulta = select(Comando)
        if equipo is not None:
            consulta = consulta.where(Comando.equipo_id == equipo.id_equipo)
        if estado is not None:
            consulta = consulta.where(Comando.estado == estado)
        return list(self.s.scalars(consulta.order_by(Comando.fecha_orden.desc()).limit(limite)))


class BitacoraRepositorySql(BitacoraRepository):
    def __init__(self, s: Session):
        self.s = s

    def agregar(self, en: EntradaBitacora) -> None:
        self.s.add(en)
        self.s.flush()

    def de_comando(self, id_comando: str) -> EntradaBitacora | None:
        return self.s.scalar(select(EntradaBitacora).where(EntradaBitacora.comando_id == id_comando))

    def cerrar(self, en: EntradaBitacora) -> None:
        self.s.add(en)
        self.s.flush()

    def buscar(self, f: FiltroBitacora, limite: int) -> list[EntradaBitacora]:
        consulta = select(EntradaBitacora)
        if f.equipo_id:
            consulta = consulta.where(EntradaBitacora.equipo_id == f.equipo_id)
        if f.usuario_id:
            consulta = consulta.where(EntradaBitacora.usuario_id == f.usuario_id)
        if f.tipo_accion:
            consulta = consulta.where(EntradaBitacora.tipo_accion == f.tipo_accion)
        if f.desde:
            consulta = consulta.where(EntradaBitacora.fecha_orden >= f.desde)
        if f.hasta:
            consulta = consulta.where(EntradaBitacora.fecha_orden <= f.hasta)
        return list(self.s.scalars(consulta.order_by(EntradaBitacora.fecha_orden.desc()).limit(limite)))
