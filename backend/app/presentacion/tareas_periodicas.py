"""TareasPeriodicas (L4, componente de la capa de aplicación) — cada 60 s, dentro del proceso de la API.

Detecta equipos desconectados (ServicioDisponibilidad) y expira órdenes vencidas
(ServicioAcciones.expirar_vencidos). Supuesto del L4 §6.1: sin servicio de colas.
"""
import asyncio
import logging

from fastapi import FastAPI

from app.presentacion.dependencias import Contenedor

log = logging.getLogger("sentinela.tareas")


def ejecutar_una_vez(app: FastAPI) -> None:
    bd = app.state.fabrica_sesiones()
    try:
        c = Contenedor(bd, app.state.cfg)
        desconectados = c.disponibilidad.detectar_desconectados()
        expirados = c.acciones.expirar_vencidos()
        bd.commit()
        if desconectados or expirados:
            log.info("Desconectados: %d · órdenes expiradas: %d", len(desconectados), len(expirados))
    except Exception:
        bd.rollback()
        log.exception("Falló la tarea periódica")
    finally:
        bd.close()


async def ciclo(app: FastAPI, segundos: int) -> None:
    while True:
        await asyncio.to_thread(ejecutar_una_vez, app)
        await asyncio.sleep(segundos)
