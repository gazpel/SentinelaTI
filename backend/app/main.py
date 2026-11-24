"""Punto de entrada de la API de SentinelaTI.

Ejecutar (desde backend/):  uvicorn app.main:app --reload
Documentación interactiva del contrato (OpenAPI): http://localhost:8000/docs
"""
import asyncio
import contextlib
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.aplicacion.errores import CuentaBloqueada, NoAutenticado, NoEncontrado, PermisoDenegado
from app.config import Configuracion
from app.dominio.base import ErrorDominio
from app.dominio.usuarios import Administrador
from app.infraestructura.bd import crear_motor, crear_tablas, fabrica_sesiones
from app.infraestructura.repositorios_sql import ConfiguracionRepositorySql, UsuarioRepositorySql
from app.infraestructura.seguridad import hashear_contrasena
from app.presentacion import routers_agente, routers_panel
from app.presentacion.tareas_periodicas import ciclo

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("sentinela")


def preparar_base(app: FastAPI) -> None:
    """Crea las tablas, los umbrales por defecto y, si no hay usuarios, el administrador inicial."""
    cfg: Configuracion = app.state.cfg
    crear_tablas(app.state.motor)
    with app.state.fabrica_sesiones() as bd:
        ConfiguracionRepositorySql(bd).obtener()
        usuarios = UsuarioRepositorySql(bd)
        if not usuarios.listar():
            usuarios.guardar(Administrador(nombre="Administrador inicial", correo=cfg.correo_admin,
                                           hash_contrasena=hashear_contrasena(cfg.clave_admin),
                                           activo=True, intentos_fallidos=0))
            log.warning("Se creó el administrador inicial %s: cambie su contraseña.", cfg.correo_admin)
        bd.commit()


def crear_app(cfg: Configuracion | None = None) -> FastAPI:
    cfg = cfg or Configuracion()

    @contextlib.asynccontextmanager
    async def ciclo_de_vida(app: FastAPI):
        preparar_base(app)
        tarea = asyncio.create_task(ciclo(app, cfg.segundos_tareas)) if cfg.tareas_periodicas else None
        yield
        if tarea:
            tarea.cancel()

    app = FastAPI(title="SentinelaTI API", version="0.5.0 (prototipo L5)", lifespan=ciclo_de_vida,
                  description="IPanelAPI (/api/panel, JWT) e IAgenteAPI (/api/agente, token de agente).")
    app.state.cfg = cfg
    app.state.motor = crear_motor(cfg.url_bd)
    app.state.fabrica_sesiones = fabrica_sesiones(app.state.motor)

    app.add_middleware(CORSMiddleware, allow_origins=cfg.origenes_cors, allow_methods=["*"],
                       allow_headers=["*"])
    app.include_router(routers_panel.router)
    app.include_router(routers_agente.router)

    # Errores de aplicación y de dominio → códigos HTTP del contrato.
    def _respuesta(codigo: int):
        async def manejador(_: Request, error: Exception):
            return JSONResponse(status_code=codigo, content={"detail": str(error)})
        return manejador

    app.add_exception_handler(CuentaBloqueada, _respuesta(423))
    app.add_exception_handler(NoAutenticado, _respuesta(401))
    app.add_exception_handler(PermisoDenegado, _respuesta(403))
    app.add_exception_handler(NoEncontrado, _respuesta(404))
    app.add_exception_handler(ErrorDominio, _respuesta(422))

    @app.get("/api/salud", tags=["sistema"])
    def salud():
        return {"estado": "ok"}

    return app


app = crear_app()
