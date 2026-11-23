"""Carga datos de demostración: 20 equipos ficticios con 30 días de lecturas, alertas y órdenes.

Uso (desde backend/):
    python -m scripts.sembrar_demo            # usa SENTINELA_BD_URL o sentinela.sqlite3
    python -m scripts.sembrar_demo --reiniciar  # borra la base antes de sembrar

Crea además un usuario Técnico de prueba (tecnico@sentinela.local / Tecnico.2026).
Todos los datos son ficticios.
"""
import argparse
import math
import random
from datetime import timedelta

from sqlalchemy import insert

from app.aplicacion.servicio_enrolamiento import DatosEquipo
from app.config import Configuracion
from app.dominio.base import Base, ahora, nuevo_id
from app.dominio.enumeraciones import ModoApagado, TipoAccion
from app.dominio.monitoreo import Lectura, UsoDisco
from app.dominio.usuarios import Sesion, Tecnico
from app.infraestructura.bd import crear_motor, crear_tablas, fabrica_sesiones
from app.infraestructura.seguridad import hashear_contrasena
from app.main import crear_app, preparar_base
from app.presentacion.dependencias import Contenedor
from app.dominio.acciones import ResultadoEjecucion

# (nombre, último usuario, perfil): el perfil decide cómo se ven sus métricas.
EQUIPOS = [
    ("PC-OPS-022", "jperez", "cpu_critica"), ("PC-FIN-031", "mrojas", "disco_critico"),
    ("PC-RRHH-008", "csoto", "ram_alta"), ("PC-VEN-017", "fvaldes", "ram_alta"),
    ("PC-BOD-002", "lmunoz", "desconectado"), ("PC-ADM-040", "agarcia", "desconectado"),
    ("PC-FIN-014", "adiaz", "normal"), ("PC-FIN-015", "pnavarro", "normal"),
    ("PC-OPS-010", "rtorres", "normal"), ("PC-OPS-011", "bfuentes", "normal"),
    ("PC-OPS-012", "kreyes", "normal"), ("PC-RRHH-001", "dcastro", "normal"),
    ("PC-RRHH-002", "ivargas", "normal"), ("PC-VEN-003", "tmorales", "normal"),
    ("PC-VEN-004", "nherrera", "normal"), ("PC-ADM-005", "eortiz", "normal"),
    ("PC-ADM-006", "gsilva", "normal"), ("PC-BOD-007", "hpizarro", "normal"),
    ("PC-SOP-008", "ojara", "normal"), ("PC-SOP-009", "vespinoza", "sin_sensor"),
]
DIAS_HISTORIAL = 30
PASO = timedelta(minutes=30)
HORAS_DESDE_ARRANQUE = 26.5  # los equipos de demostración se reinician cada 72 h


def valores(perfil: str, t: float, r: random.Random) -> tuple[float, float, float, float | None]:
    """CPU, RAM, disco y temperatura con un ciclo diario (más carga en horario laboral) y ruido."""
    hora = (t / 3600) % 24
    jornada = max(0.0, math.sin((hora - 7) / 12 * math.pi))
    cpu = 12 + 45 * jornada + r.gauss(0, 6)
    ram = 45 + 20 * jornada + r.gauss(0, 4)
    disco = 55 + r.gauss(0, 0.5)
    if perfil == "ram_alta":
        ram += 30
    if perfil == "disco_critico":
        disco = 97
    temperatura = None if perfil == "sin_sensor" else 42 + cpu * 0.35 + r.gauss(0, 2)
    clamp = lambda v: max(0.0, min(100.0, v))
    return clamp(cpu), clamp(ram), clamp(disco), temperatura


def sembrar(cfg: Configuracion, reiniciar: bool) -> None:
    motor = crear_motor(cfg.url_bd)
    if reiniciar:
        Base.metadata.drop_all(motor)
    crear_tablas(motor)
    app = crear_app(cfg)
    app.state.motor, app.state.fabrica_sesiones = motor, fabrica_sesiones(motor)
    preparar_base(app)
    r = random.Random(2026)
    momento = ahora()

    with app.state.fabrica_sesiones() as bd:
        c = Contenedor(bd, cfg)
        if c.usuarios.obtener_por_correo("tecnico@sentinela.local") is None:
            c.usuarios.guardar(Tecnico(nombre="Técnico de turno", correo="tecnico@sentinela.local",
                                       hash_contrasena=hashear_contrasena("Tecnico.2026"), activo=True,
                                       intentos_fallidos=0))
        admin = c.usuarios.obtener_por_correo(cfg.correo_admin)
        tecnico = c.usuarios.obtener_por_correo("tecnico@sentinela.local")
        tokens = {}
        for i, (nombre, usuario, perfil) in enumerate(EQUIPOS):
            equipo, token = c.enrolamiento.enrolar(cfg.codigo_enrolamiento, DatosEquipo(
                nombre=nombre, numero_serie=f"DEMO-{1000 + i}", modelo=r.choice(["HP ProDesk 400 G7", "Lenovo ThinkCentre M70q", "Dell OptiPlex 7090"]),
                sistema_operativo=r.choice(["Windows 11 Pro 23H2", "Windows 10 Pro 22H2"]),
                direccion_ip=f"10.0.1.{10 + i}", ultimo_usuario=usuario))
            equipo.fecha_enrolamiento = momento - timedelta(days=DIAS_HISTORIAL + 1)
            tokens[nombre] = (equipo, token)
            fin = momento - (timedelta(hours=3) if perfil == "desconectado" else timedelta(minutes=r.randint(1, 4)))
            # Historial masivo con inserciones directas (rápido); la última lectura pasa por el servicio.
            filas_lectura, filas_disco = [], []
            t = fin - timedelta(days=DIAS_HISTORIAL)
            ultimo_arranque = fin - timedelta(hours=HORAS_DESDE_ARRANQUE)
            while t < fin - PASO:
                cpu, ram, disco, temp = valores(perfil, t.timestamp(), r)
                id_l = nuevo_id()
                filas_lectura.append(dict(id_lectura=id_l, equipo_id=equipo.id_equipo, marca_tiempo=t, uso_cpu=cpu,
                                          uso_ram=ram, temperatura_cpu=temp, horas_encendido=((t - ultimo_arranque).total_seconds() / 3600) % 72))
                filas_disco.append(dict(id_uso=nuevo_id(), lectura_id=id_l, unidad="C:", uso_porcentaje=disco))
                t += PASO
            bd.execute(insert(Lectura), filas_lectura)
            bd.execute(insert(UsoDisco), filas_disco)
            cpu, ram, disco, temp = valores(perfil, fin.timestamp(), r)
            if perfil == "cpu_critica":
                cpu = 98.5
            c.recepcion.recibir_lectura(token, Lectura(
                marca_tiempo=fin, uso_cpu=cpu, uso_ram=ram, temperatura_cpu=temp, horas_encendido=HORAS_DESDE_ARRANQUE,
                discos=[UsoDisco(unidad="C:", uso_porcentaje=disco), UsoDisco(unidad="D:", uso_porcentaje=31.0)]))
        c.disponibilidad.detectar_desconectados()

        # Órdenes de ejemplo con distintos desenlaces, para la bitácora y la vista Acciones.
        s_admin = Sesion("demo", admin, "", momento + timedelta(hours=1))
        s_tec = Sesion("demo", tecnico, "", momento + timedelta(hours=1))

        def orden(sesion, nombre, tipo, p, desenlace, hace):
            equipo, token = tokens[nombre]
            comando = c.acciones.crear_comando(sesion, equipo.id_equipo, tipo, p)
            if desenlace == "cancelar":
                c.acciones.cancelar(sesion, comando.id_comando)
            elif desenlace in ("ok", "falla"):
                c.acciones.comandos_pendientes(token)
                c.acciones.registrar_resultado(token, comando.id_comando, ResultadoEjecucion(
                    desenlace == "ok", None if desenlace == "ok" else "El usuario canceló el apagado (código 1116)."))
            # Se reparte la historia en los días anteriores (solo para que la demostración sea realista).
            entrada = c.registros_bitacora.de_comando(comando.id_comando)
            for objeto, campos in ((comando, ("fecha_orden", "fecha_entrega", "fecha_resultado")),
                                   (entrada, ("fecha_orden", "fecha_resultado"))):
                for campo in campos:
                    if getattr(objeto, campo):
                        setattr(objeto, campo, getattr(objeto, campo) - hace)

        orden(s_tec, "PC-FIN-014", TipoAccion.REINICIAR_APAGAR, {"modo": ModoApagado.REINICIAR.value}, "ok", timedelta(days=6, hours=3))
        orden(s_tec, "PC-OPS-010", TipoAccion.REINICIAR_APAGAR, {"modo": ModoApagado.APAGAR.value}, "falla", timedelta(days=4, hours=7))
        orden(s_admin, "PC-RRHH-008", TipoAccion.REINICIAR_APAGAR, {"modo": ModoApagado.REINICIAR.value}, "cancelar", timedelta(days=2, hours=1))
        orden(s_admin, "PC-SOP-009", TipoAccion.FORMATEAR, {"nombreConfirmado": "PC-SOP-009"}, "ok", timedelta(days=1, hours=5))
        orden(s_tec, "PC-BOD-002", TipoAccion.REINICIAR_APAGAR, {"modo": ModoApagado.REINICIAR.value}, "pendiente", timedelta(minutes=40))
        bd.commit()
    print(f"Listo: {len(EQUIPOS)} equipos, {DIAS_HISTORIAL} días de lecturas cada {int(PASO.total_seconds() // 60)} min.")
    print(f"Administrador: {cfg.correo_admin} / {cfg.clave_admin} · Técnico: tecnico@sentinela.local / Tecnico.2026")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--reiniciar", action="store_true", help="Borra todas las tablas antes de sembrar")
    sembrar(Configuracion(), p.parse_args().reiniciar)
