"""ServicioUsuarios (L4, cambio C3) — RF13, CU10."""
import re

from app.aplicacion.errores import DatosInvalidos, NoEncontrado
from app.aplicacion.servicio_autenticacion import ServicioAutenticacion
from app.dominio.enumeraciones import Permiso, Rol
from app.dominio.repositorios import UsuarioRepository
from app.dominio.usuarios import Sesion, Usuario, clase_para_rol
from app.infraestructura import seguridad

LARGO_MINIMO_CLAVE = 8
_PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ServicioUsuarios:
    def __init__(self, usuarios: UsuarioRepository, autenticacion: ServicioAutenticacion):
        self.usuarios = usuarios
        self.autenticacion = autenticacion

    def crear_usuario(self, s: Sesion, nombre: str, correo: str, rol: Rol, clave: str) -> Usuario:
        self.autenticacion.autorizar(s, Permiso.GESTIONAR_USUARIOS)
        nombre, correo = nombre.strip(), correo.strip().lower()
        self._validar_nombre(nombre)
        if not _PATRON_CORREO.match(correo):
            raise DatosInvalidos("El correo no tiene un formato válido.")
        if self.usuarios.obtener_por_correo(correo) is not None:
            raise DatosInvalidos("Ya existe un usuario con ese correo.")
        if len(clave) < LARGO_MINIMO_CLAVE:
            raise DatosInvalidos(f"La contraseña debe tener al menos {LARGO_MINIMO_CLAVE} caracteres.")
        usuario = clase_para_rol(rol)(nombre=nombre, correo=correo,
                                      hash_contrasena=seguridad.hashear_contrasena(clave), activo=True,
                                      intentos_fallidos=0)
        self.usuarios.guardar(usuario)
        return usuario

    def editar_usuario(self, s: Sesion, id_usuario: str, nombre: str, rol: Rol) -> Usuario:
        self.autenticacion.autorizar(s, Permiso.GESTIONAR_USUARIOS)
        usuario = self._obtener(id_usuario)
        nombre = nombre.strip()
        self._validar_nombre(nombre)
        if usuario.id_usuario == s.usuario.id_usuario and rol is not usuario.rol():
            raise DatosInvalidos("No puede cambiar su propio rol.")
        usuario.nombre = nombre
        usuario.tipo_rol = rol.value  # cambia la subclase (tabla única) desde la próxima lectura
        self.usuarios.guardar(usuario)
        return usuario

    def desactivar_usuario(self, s: Sesion, id_usuario: str) -> Usuario:
        self.autenticacion.autorizar(s, Permiso.GESTIONAR_USUARIOS)
        usuario = self._obtener(id_usuario)
        if usuario.id_usuario == s.usuario.id_usuario:
            raise DatosInvalidos("No puede desactivar su propia cuenta.")
        usuario.desactivar()
        self.usuarios.guardar(usuario)
        return usuario

    def listar(self, s: Sesion) -> list[Usuario]:
        self.autenticacion.autorizar(s, Permiso.GESTIONAR_USUARIOS)
        return self.usuarios.listar()

    def _obtener(self, id_usuario: str) -> Usuario:
        usuario = self.usuarios.obtener_por_id(id_usuario)
        if usuario is None:
            raise NoEncontrado("El usuario no existe.")
        return usuario

    @staticmethod
    def _validar_nombre(nombre: str) -> None:
        if not (2 <= len(nombre) <= 120):
            raise DatosInvalidos("El nombre debe tener entre 2 y 120 caracteres.")
