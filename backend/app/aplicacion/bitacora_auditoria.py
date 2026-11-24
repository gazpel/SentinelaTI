"""BitacoraAuditoria (L4) — RF14, RF18, RNF12 (decisión D11)."""
from app.aplicacion.errores import DatosInvalidos
from app.aplicacion.servicio_autenticacion import ServicioAutenticacion
from app.dominio.acciones import Comando
from app.dominio.auditoria import EntradaBitacora, FiltroBitacora
from app.dominio.base import ahora
from app.dominio.enumeraciones import EstadoComando, Permiso, TipoAccion
from app.dominio.monitoreo import Equipo
from app.dominio.repositorios import BitacoraRepository
from app.dominio.usuarios import Sesion, Usuario

LIMITE_CONSULTA = 500


class BitacoraAuditoria:
    def __init__(self, bitacora: BitacoraRepository, autenticacion: ServicioAutenticacion | None = None):
        self.bitacora = bitacora
        self.autenticacion = autenticacion

    def registrar_orden(self, c: Comando, u: Usuario) -> EntradaBitacora:
        """Abre la única entrada del comando. Se escribe antes de que la orden exista para el
        agente: si esta escritura falla, la transacción completa se revierte (D11)."""
        entrada = EntradaBitacora(
            comando_id=c.id_comando, fecha_orden=c.fecha_orden, tipo_accion=c.tipo(),
            descripcion=c.descripcion(), estado_resultante=EstadoComando.PENDIENTE,
            usuario_id=u.id_usuario, nombre_usuario=u.nombre,
            equipo_id=c.equipo.id_equipo, nombre_equipo=c.equipo.nombre, cerrada=False)
        self.bitacora.agregar(entrada)
        return entrada

    def cerrar_entrada(self, c: Comando, estado: EstadoComando) -> EntradaBitacora:
        entrada = self.bitacora.de_comando(c.id_comando)
        entrada.cerrar(estado, c.fecha_resultado)
        self.bitacora.cerrar(entrada)
        return entrada

    def registrar_intento_denegado(self, u: Usuario, e: Equipo, t: TipoAccion) -> EntradaBitacora:
        momento = ahora()
        entrada = EntradaBitacora(
            comando_id=None, fecha_orden=momento, fecha_resultado=momento, tipo_accion=t,
            descripcion="Intento sin permiso", estado_resultante=EstadoComando.DENEGADO,
            usuario_id=u.id_usuario, nombre_usuario=u.nombre,
            equipo_id=e.id_equipo, nombre_equipo=e.nombre, cerrada=True)
        self.bitacora.agregar(entrada)
        return entrada

    def consultar(self, s: Sesion, f: FiltroBitacora) -> list[EntradaBitacora]:
        self.autenticacion.autorizar(s, Permiso.CONSULTAR_BITACORA)
        if not f.es_valido():
            raise DatosInvalidos("La fecha «desde» no puede ser posterior a «hasta».")
        return self.bitacora.buscar(f, LIMITE_CONSULTA)
