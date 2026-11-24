"""Pruebas unitarias del dominio (sin base de datos ni HTTP)."""
from datetime import datetime, timedelta

import pytest

from app.dominio.acciones import ComandoFormateo, ComandoReinicioApagado, ResultadoEjecucion, TransicionInvalida
from app.dominio.auditoria import EntradaBitacora
from app.dominio.base import ErrorDominio
from app.dominio.enumeraciones import EstadoComando, ModoApagado, NivelAlerta, Permiso, TipoAccion
from app.dominio.monitoreo import Equipo, Umbral
from app.dominio.usuarios import Administrador, Tecnico

T0 = datetime(2026, 11, 20, 12, 0)


def comando_pendiente():
    c = ComandoReinicioApagado(modo=ModoApagado.REINICIAR)
    c.estado, c.fecha_orden = EstadoComando.PENDIENTE, T0
    return c


def test_transiciones_validas_del_comando():
    c = comando_pendiente()
    c.marcar_entregado(T0)
    c.registrar_resultado(ResultadoEjecucion(True), T0)
    assert c.estado == EstadoComando.EJECUTADO


@pytest.mark.parametrize("accion", ["registrar", "expirar_dos_veces", "cancelar_entregado"])
def test_transiciones_invalidas_del_comando(accion):
    c = comando_pendiente()
    with pytest.raises(TransicionInvalida):
        if accion == "registrar":
            c.registrar_resultado(ResultadoEjecucion(True))
        elif accion == "expirar_dos_veces":
            c.expirar(); c.expirar()
        else:
            c.marcar_entregado(); c.cancelar()


def test_expiracion_valores_limite():
    c = comando_pendiente()
    assert not c.ha_expirado(T0 + timedelta(hours=24))
    assert c.ha_expirado(T0 + timedelta(hours=24, seconds=1))
    c.marcar_entregado(T0)
    assert not c.ha_expirado(T0 + timedelta(minutes=60))
    assert c.ha_expirado(T0 + timedelta(minutes=60, seconds=1))


def test_confirmacion_de_formateo_es_exacta():
    e = Equipo(nombre="PC-OPS-022")
    assert ComandoFormateo(nombre_confirmado="PC-OPS-022").confirmacion_valida(e)
    assert not ComandoFormateo(nombre_confirmado="pc-ops-022").confirmacion_valida(e)


@pytest.mark.parametrize("valor, nivel", [(None, NivelAlerta.NORMAL), (80, NivelAlerta.NORMAL),
                                          (80.01, NivelAlerta.ADVERTENCIA), (95, NivelAlerta.ADVERTENCIA),
                                          (95.01, NivelAlerta.CRITICO)])
def test_umbral_evaluar(valor, nivel):
    assert Umbral(valor_advertencia=80, valor_critico=95).evaluar(valor) is nivel


def test_permisos_por_rol_tabla_5():
    tec, adm = Tecnico(), Administrador()
    assert not tec.tiene_permiso(Permiso.FORMATEAR) and adm.tiene_permiso(Permiso.FORMATEAR)
    assert TipoAccion.FORMATEAR.permiso_requerido() is Permiso.FORMATEAR
    assert TipoAccion.REINICIAR_APAGAR.permiso_requerido() is Permiso.ORDENAR_ACCION


def test_entrada_de_bitacora_cerrada_es_inmutable():
    en = EntradaBitacora(cerrada=False)
    en.cerrar(EstadoComando.EJECUTADO, T0)
    assert en.es_inmutable()
    with pytest.raises(ErrorDominio):
        en.cerrar(EstadoComando.FALLIDO, T0)


def test_entrada_no_se_cierra_con_estado_intermedio():
    with pytest.raises(ErrorDominio):
        EntradaBitacora(cerrada=False).cerrar(EstadoComando.ENTREGADO)


def test_bloqueo_por_intentos():
    u = Tecnico(intentos_fallidos=0)
    for _ in range(4):
        u.registrar_intento_fallido(T0)
    assert not u.esta_bloqueado(T0)
    u.registrar_intento_fallido(T0)
    assert u.esta_bloqueado(T0 + timedelta(minutes=14, seconds=59))
    assert not u.esta_bloqueado(T0 + timedelta(minutes=15))
