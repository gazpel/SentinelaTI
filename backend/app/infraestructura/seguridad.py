"""Primitivas criptográficas: hash de contraseñas y JWT del panel (RNF01, RF17)."""
import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timezone

import jwt

_ITERACIONES = 210_000  # PBKDF2-HMAC-SHA256, recomendación OWASP 2023
_ALGORITMO_JWT = "HS256"


def hashear_contrasena(clave: str) -> str:
    sal = os.urandom(16)
    derivada = hashlib.pbkdf2_hmac("sha256", clave.encode(), sal, _ITERACIONES)
    return "pbkdf2_sha256${}${}${}".format(
        _ITERACIONES, base64.b64encode(sal).decode(), base64.b64encode(derivada).decode())


def verificar_contrasena(clave: str, almacenado: str) -> bool:
    try:
        _, iteraciones, sal, derivada = almacenado.split("$")
    except ValueError:
        return False
    calculada = hashlib.pbkdf2_hmac("sha256", clave.encode(), base64.b64decode(sal), int(iteraciones))
    return hmac.compare_digest(calculada, base64.b64decode(derivada))


def nuevo_token_agente() -> str:
    return secrets.token_urlsafe(32)


def emitir_jwt(secreto: str, id_usuario: str, id_sesion: str, expira: datetime) -> str:
    carga = {"sub": id_usuario, "sid": id_sesion, "exp": expira.replace(tzinfo=timezone.utc)}
    return jwt.encode(carga, secreto, algorithm=_ALGORITMO_JWT)


def leer_jwt(secreto: str, token: str) -> dict | None:
    """Devuelve la carga del JWT, o None si la firma no es válida o expiró."""
    try:
        return jwt.decode(token, secreto, algorithms=[_ALGORITMO_JWT])
    except jwt.PyJWTError:
        return None
