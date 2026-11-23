"""RoutersAgente (L4) — interfaz IAgenteAPI bajo /api/agente, autenticada con el token del agente (RNF01).

El agente siempre inicia la comunicación (decisión D2): envía lecturas y
consulta sus órdenes pendientes; el servidor nunca se conecta al equipo.
"""
from datetime import timedelta, timezone

from fastapi import APIRouter, Depends, status

from app.aplicacion.errores import DatosInvalidos
from app.aplicacion.servicio_enrolamiento import DatosEquipo
from app.dominio.acciones import ResultadoEjecucion
from app.dominio.base import ahora
from app.dominio.monitoreo import Lectura, UsoDisco
from app.presentacion import esquemas as E
from app.presentacion.dependencias import Contenedor, obtener_contenedor, token_agente

router = APIRouter(prefix="/api/agente", tags=["agente"])

TOLERANCIA_RELOJ = timedelta(minutes=5)


@router.post("/enrolamiento", response_model=E.EnrolamientoSalida, status_code=status.HTTP_201_CREATED)
def enrolar(datos: E.EnrolamientoEntrada, c: Contenedor = Depends(obtener_contenedor)):
    """RF01: con un código vigente se registra el equipo y se le entrega su token propio."""
    equipo, token = c.enrolamiento.enrolar(datos.codigo, DatosEquipo(
        nombre=datos.nombre, numero_serie=datos.numero_serie, modelo=datos.modelo,
        sistema_operativo=datos.sistema_operativo, direccion_ip=datos.direccion_ip,
        ultimo_usuario=datos.ultimo_usuario))
    return E.EnrolamientoSalida(id_equipo=equipo.id_equipo, token=token,
                                intervalo_reporte_min=c.cfg.intervalo_reporte_min)


@router.post("/lecturas", response_model=E.RespuestaLectura)
def recibir_lectura(datos: E.LecturaEntrada, token: str | None = Depends(token_agente),
                    c: Contenedor = Depends(obtener_contenedor)):
    """RF02. Una lectura repetida (misma marca de tiempo) se acepta sin duplicarla (RNF04)."""
    marca = datos.marca_tiempo
    if marca.tzinfo is not None:
        marca = marca.astimezone(timezone.utc).replace(tzinfo=None)
    if marca > ahora() + TOLERANCIA_RELOJ:
        raise DatosInvalidos("La marca de tiempo de la lectura está en el futuro.")
    lectura = Lectura(
        marca_tiempo=marca, uso_cpu=datos.uso_cpu, uso_ram=datos.uso_ram,
        temperatura_cpu=datos.temperatura_cpu, horas_encendido=datos.horas_encendido,
        discos=[UsoDisco(unidad=d.unidad, uso_porcentaje=d.uso_porcentaje) for d in datos.discos])
    nueva = c.recepcion.recibir_lectura(token, lectura)
    return E.RespuestaLectura(registrada=nueva, duplicada=not nueva)


@router.get("/comandos/pendientes", response_model=list[E.OrdenSalida])
def comandos_pendientes(token: str | None = Depends(token_agente), c: Contenedor = Depends(obtener_contenedor)):
    """Sondeo cada 60 s (D2). Las órdenes devueltas pasan a Entregado."""
    return [E.OrdenSalida(id_comando=o.id_comando, tipo=o.tipo, parametros=o.parametros,
                          interrumpe_uso=o.interrumpe_uso, simulado=o.simulado)
            for o in c.acciones.comandos_pendientes(token)]


@router.post("/comandos/{id_comando}/resultado", status_code=status.HTTP_204_NO_CONTENT)
def registrar_resultado(id_comando: str, datos: E.ResultadoEntrada, token: str | None = Depends(token_agente),
                        c: Contenedor = Depends(obtener_contenedor)):
    c.acciones.registrar_resultado(token, id_comando, ResultadoEjecucion(exito=datos.exito, mensaje=datos.mensaje))
