"""RoutersPanel (L4) — interfaz IPanelAPI bajo /api/panel, protegida con JWT (RF17).

Los routers solo traducen HTTP ↔ servicios: no contienen reglas de negocio.
La bitácora expone únicamente GET: no hay edición ni borrado (RNF12).
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, status

from app.dominio.acciones import Comando
from app.dominio.auditoria import EntradaBitacora, FiltroBitacora
from app.dominio.enumeraciones import EstadoComando, EstadoEquipo, Metrica, Permiso, TipoAccion
from app.dominio.monitoreo import RANGOS_UMBRAL, Alerta, Equipo, Lectura, Umbral
from app.dominio.usuarios import Sesion, Usuario
from app.presentacion import esquemas as E
from app.presentacion.dependencias import Contenedor, obtener_contenedor, sesion_actual

router = APIRouter(prefix="/api/panel", tags=["panel"])


# ------------------------------------------------------------------ conversión a JSON
def usuario_json(u: Usuario) -> E.UsuarioSalida:
    return E.UsuarioSalida(id_usuario=u.id_usuario, nombre=u.nombre, correo=u.correo, rol=u.rol(),
                           activo=u.activo, permisos=sorted(p.value for p in u.PERMISOS))


def equipo_resumen_json(e: Equipo) -> E.EquipoResumen:
    return E.EquipoResumen.model_validate(e)


def lectura_json(l: Lectura) -> E.LecturaSalida:
    return E.LecturaSalida(
        marca_tiempo=l.marca_tiempo, uso_cpu=l.uso_cpu, uso_ram=l.uso_ram,
        temperatura_cpu=l.temperatura_cpu, horas_encendido=l.horas_encendido,
        discos=[E.UsoDiscoSalida.model_validate(d) for d in sorted(l.discos, key=lambda d: d.unidad)],
        uso_disco_max=l.valor_de(Metrica.DISCO))


def alerta_json(a: Alerta) -> E.AlertaSalida:
    return E.AlertaSalida(id_alerta=a.id_alerta, id_equipo=a.equipo_id, nombre_equipo=a.equipo.nombre,
                          metrica=a.metrica, nivel=a.nivel, valor=a.valor, fecha_apertura=a.fecha_apertura)


def umbral_json(u: Umbral) -> E.UmbralSalida:
    rango = RANGOS_UMBRAL[u.metrica]
    return E.UmbralSalida(metrica=u.metrica, advertencia=u.valor_advertencia, critico=u.valor_critico,
                          minimo=rango.minimo, maximo=rango.maximo, unidad=rango.unidad)


def comando_json(c: Comando) -> E.ComandoSalida:
    return E.ComandoSalida(
        id_comando=c.id_comando, id_equipo=c.equipo_id, nombre_equipo=c.equipo.nombre, tipo=c.tipo(),
        descripcion=c.descripcion(), estado=c.estado, simulado=c.simulado, ordenado_por=c.usuario.nombre,
        fecha_orden=c.fecha_orden, fecha_entrega=c.fecha_entrega, fecha_resultado=c.fecha_resultado,
        motivo_fallo=c.motivo_fallo)


def entrada_json(en: EntradaBitacora) -> E.EntradaBitacoraSalida:
    return E.EntradaBitacoraSalida.model_validate(en)


def _utc_sin_zona(d: datetime | None) -> datetime | None:
    if d is None or d.tzinfo is None:
        return d
    return d.astimezone(timezone.utc).replace(tzinfo=None)


# ------------------------------------------------------------------ sesión (RF17, CU03)
@router.post("/sesion", response_model=E.SesionSalida)
def iniciar_sesion(datos: E.SolicitudInicioSesion, c: Contenedor = Depends(obtener_contenedor)):
    sesion = c.autenticacion.iniciar_sesion(datos.correo, datos.clave)
    return E.SesionSalida(token=sesion.token_jwt, expira=sesion.fecha_expiracion, usuario=usuario_json(sesion.usuario))


@router.get("/sesion", response_model=E.UsuarioSalida)
def sesion_vigente(s: Sesion = Depends(sesion_actual)):
    return usuario_json(s.usuario)


# ------------------------------------------------------------------ parque (RF05, RF06)
@router.get("/equipos", response_model=E.ListadoEquipos)
def listar_equipos(estado: EstadoEquipo | None = None, texto: str | None = Query(default=None, max_length=100),
                   pagina: int = 1, tamano: int = 25,
                   s: Sesion = Depends(sesion_actual), c: Contenedor = Depends(obtener_contenedor)):
    equipos, total = c.parque.listar(s, estado, texto, pagina, tamano)
    return E.ListadoEquipos(items=[equipo_resumen_json(e) for e in equipos], total=total, pagina=pagina,
                            tamano=tamano, resumen=c.parque.resumen_por_estado(s),
                            alertas_abiertas=c.gestor_alertas.contar_abiertas(s))


@router.get("/equipos/{id_equipo}", response_model=E.EquipoDetalle)
def detalle_equipo(id_equipo: str, s: Sesion = Depends(sesion_actual), c: Contenedor = Depends(obtener_contenedor)):
    equipo, ultima, alertas = c.parque.detalle(s, id_equipo)
    base = equipo_resumen_json(equipo).model_dump()
    return E.EquipoDetalle(
        **base, numero_serie=equipo.numero_serie, modelo=equipo.modelo,
        sistema_operativo=equipo.sistema_operativo, fecha_enrolamiento=equipo.fecha_enrolamiento,
        ultima_lectura=lectura_json(ultima) if ultima else None, alertas_abiertas=[alerta_json(a) for a in alertas])


@router.get("/equipos/{id_equipo}/lecturas", response_model=list[E.LecturaSalida])
def historial_equipo(id_equipo: str, rango: str = "24h",
                     s: Sesion = Depends(sesion_actual), c: Contenedor = Depends(obtener_contenedor)):
    return [lectura_json(l) for l in c.parque.historial(s, id_equipo, rango)]


# ------------------------------------------------------------------ acciones (RF08, RF11)
@router.post("/equipos/{id_equipo}/comandos", response_model=E.ComandoSalida, status_code=status.HTTP_201_CREATED)
def ordenar_accion(id_equipo: str, datos: E.ComandoEntrada,
                   s: Sesion = Depends(sesion_actual), c: Contenedor = Depends(obtener_contenedor)):
    parametros = {k: v for k, v in {"modo": datos.modo, "nombreConfirmado": datos.nombre_confirmado}.items() if v}
    return comando_json(c.acciones.crear_comando(s, id_equipo, datos.tipo, parametros))


@router.get("/comandos", response_model=list[E.ComandoSalida])
def listar_comandos(equipo: str | None = None, estado: EstadoComando | None = None,
                    s: Sesion = Depends(sesion_actual), c: Contenedor = Depends(obtener_contenedor)):
    return [comando_json(x) for x in c.acciones.listar(s, equipo, estado)]


@router.post("/comandos/{id_comando}/cancelar", response_model=E.ComandoSalida)
def cancelar_comando(id_comando: str, s: Sesion = Depends(sesion_actual), c: Contenedor = Depends(obtener_contenedor)):
    return comando_json(c.acciones.cancelar(s, id_comando))


# ------------------------------------------------------------------ alertas (RF16)
@router.get("/alertas", response_model=E.ListadoAlertas)
def listar_alertas(pagina: int = Query(default=1, ge=1), tamano: int = Query(default=50, ge=1, le=100),
                   s: Sesion = Depends(sesion_actual), c: Contenedor = Depends(obtener_contenedor)):
    alertas, total = c.gestor_alertas.consultar_abiertas(s, pagina, tamano)
    return E.ListadoAlertas(items=[alerta_json(a) for a in alertas], total=total)


# ------------------------------------------------------------------ umbrales (RF07)
@router.get("/umbrales", response_model=list[E.UmbralSalida])
def obtener_umbrales(s: Sesion = Depends(sesion_actual), c: Contenedor = Depends(obtener_contenedor)):
    return [umbral_json(u) for u in c.servicio_configuracion.obtener_configuracion().umbrales()]


@router.put("/umbrales/{metrica}", response_model=E.UmbralSalida)
def definir_umbral(metrica: Metrica, datos: E.UmbralEntrada,
                   s: Sesion = Depends(sesion_actual), c: Contenedor = Depends(obtener_contenedor)):
    return umbral_json(c.servicio_configuracion.definir_umbral(s, metrica, datos.advertencia, datos.critico))


# ------------------------------------------------------------------ usuarios (RF13)
@router.get("/usuarios", response_model=list[E.UsuarioSalida])
def listar_usuarios(s: Sesion = Depends(sesion_actual), c: Contenedor = Depends(obtener_contenedor)):
    return [usuario_json(u) for u in c.servicio_usuarios.listar(s)]


@router.post("/usuarios", response_model=E.UsuarioSalida, status_code=status.HTTP_201_CREATED)
def crear_usuario(datos: E.UsuarioEntrada, s: Sesion = Depends(sesion_actual), c: Contenedor = Depends(obtener_contenedor)):
    return usuario_json(c.servicio_usuarios.crear_usuario(s, datos.nombre, datos.correo, datos.rol, datos.clave))


@router.put("/usuarios/{id_usuario}", response_model=E.UsuarioSalida)
def editar_usuario(id_usuario: str, datos: E.UsuarioEdicion,
                   s: Sesion = Depends(sesion_actual), c: Contenedor = Depends(obtener_contenedor)):
    usuario = c.servicio_usuarios.editar_usuario(s, id_usuario, datos.nombre, datos.rol)
    c.bd.flush()
    c.bd.expunge(usuario)  # se vuelve a leer para que tome la subclase del nuevo rol
    return usuario_json(c.usuarios.obtener_por_id(id_usuario))


@router.post("/usuarios/{id_usuario}/desactivar", response_model=E.UsuarioSalida)
def desactivar_usuario(id_usuario: str, s: Sesion = Depends(sesion_actual), c: Contenedor = Depends(obtener_contenedor)):
    return usuario_json(c.servicio_usuarios.desactivar_usuario(s, id_usuario))


# ------------------------------------------------------------------ bitácora (RF18, solo lectura)
@router.get("/bitacora", response_model=list[E.EntradaBitacoraSalida])
def consultar_bitacora(equipo: str | None = None, usuario: str | None = None, tipo: TipoAccion | None = None,
                       desde: datetime | None = None, hasta: datetime | None = None,
                       s: Sesion = Depends(sesion_actual), c: Contenedor = Depends(obtener_contenedor)):
    filtro = FiltroBitacora(equipo_id=equipo, usuario_id=usuario, tipo_accion=tipo,
                            desde=_utc_sin_zona(desde), hasta=_utc_sin_zona(hasta))
    return [entrada_json(en) for en in c.bitacora.consultar(s, filtro)]


@router.get("/bitacora/usuarios", response_model=list[E.UsuarioSalida])
def usuarios_para_filtro(s: Sesion = Depends(sesion_actual), c: Contenedor = Depends(obtener_contenedor)):
    """Lista mínima para el filtro «usuario» de la bitácora (los técnicos no gestionan usuarios)."""
    c.autenticacion.autorizar(s, Permiso.CONSULTAR_BITACORA)
    return [usuario_json(u) for u in c.usuarios.listar()]
