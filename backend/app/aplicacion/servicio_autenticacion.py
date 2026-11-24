"""ServicioAutenticacion (L4) — RF17, CU03, RNF07 (decisión D7: autorización en un único servicio)."""
from datetime import datetime, timedelta, timezone

from app.aplicacion.errores import CuentaBloqueada, NoAutenticado, PermisoDenegado
from app.dominio.base import ahora, nuevo_id
from app.dominio.enumeraciones import Permiso
from app.dominio.repositorios import UsuarioRepository
from app.dominio.usuarios import Sesion
from app.infraestructura import seguridad

MENSAJE_GENERICO = "Correo o contraseña incorrectos."  # CU03 3b: no revela qué dato falló


class ServicioAutenticacion:
    def __init__(self, usuarios: UsuarioRepository, secreto_jwt: str, horas_sesion: int = 8):
        self.usuarios = usuarios
        self.secreto_jwt = secreto_jwt
        self.horas_sesion = horas_sesion

    def iniciar_sesion(self, correo: str, clave: str) -> Sesion:
        usuario = self.usuarios.obtener_por_correo(correo)
        if usuario is None:
            raise NoAutenticado(MENSAJE_GENERICO)
        if usuario.esta_bloqueado():
            raise CuentaBloqueada("La cuenta está bloqueada por 15 minutos tras 5 intentos fallidos.")
        if not seguridad.verificar_contrasena(clave, usuario.hash_contrasena):
            usuario.registrar_intento_fallido()
            self.usuarios.guardar(usuario)
            raise NoAutenticado(MENSAJE_GENERICO, conservar_cambios=True)
        if not usuario.activo:  # CU03 3c
            raise NoAutenticado("La cuenta está desactivada. Contacte al administrador de TI.")
        usuario.registrar_ingreso_exitoso()
        self.usuarios.guardar(usuario)

        expira = ahora() + timedelta(hours=self.horas_sesion)
        id_sesion = nuevo_id()
        token = seguridad.emitir_jwt(self.secreto_jwt, usuario.id_usuario, id_sesion, expira)
        return Sesion(id_sesion=id_sesion, usuario=usuario, token_jwt=token, fecha_expiracion=expira)

    def validar_sesion(self, token_jwt: str | None) -> Sesion:
        carga = seguridad.leer_jwt(self.secreto_jwt, token_jwt) if token_jwt else None
        if carga is None:
            raise NoAutenticado("Debe iniciar sesión.")
        usuario = self.usuarios.obtener_por_id(carga["sub"])
        expira = datetime.fromtimestamp(carga["exp"], tz=timezone.utc).replace(tzinfo=None)
        if usuario is None:
            raise NoAutenticado("Debe iniciar sesión.")
        sesion = Sesion(id_sesion=carga["sid"], usuario=usuario, token_jwt=token_jwt, fecha_expiracion=expira)
        if not sesion.esta_vigente():  # un usuario desactivado pierde la sesión de inmediato
            raise NoAutenticado("La sesión expiró o la cuenta fue desactivada.")
        return sesion

    def autorizar(self, s: Sesion, p: Permiso) -> None:
        if not s.usuario.tiene_permiso(p):
            raise PermisoDenegado()
