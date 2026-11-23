"""Ejecución del agente en primer plano (el servicio de Windows, RNF02, queda para el L6).

    python -m sentinela_agente --servidor http://localhost:8000 --codigo SENTINELA-DEMO-2026
"""
import argparse
import logging
from pathlib import Path

from .agente import AgenteSentinela
from .config import ConfiguracionAgente, ConfiguracionInvalida


def main() -> None:
    p = argparse.ArgumentParser(prog="sentinela_agente", description="Agente de monitoreo SentinelaTI")
    p.add_argument("--servidor", help="URL de la API (por defecto SENTINELA_SERVIDOR o http://localhost:8000)")
    p.add_argument("--codigo", help="Código de enrolamiento de la organización")
    p.add_argument("--intervalo", type=int, default=5, help="Minutos entre lecturas (1 a 60, RF02)")
    p.add_argument("--sondeo", type=int, default=60, help="Segundos entre consultas de órdenes")
    p.add_argument("--aviso", type=int, default=300, help="Segundos de aviso antes de reiniciar (RF15)")
    p.add_argument("--datos", type=Path, help="Carpeta de datos del agente (token y cola local)")
    p.add_argument("--una-vez", action="store_true", help="Envía una lectura, revisa órdenes y termina")
    a = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        cfg = ConfiguracionAgente(intervalo_reporte_min=a.intervalo, intervalo_comandos_seg=a.sondeo,
                                  segundos_aviso=a.aviso)
    except ConfiguracionInvalida as error:
        p.error(str(error))
    if a.servidor:
        cfg.url_servidor = a.servidor
    if a.codigo:
        cfg.codigo_enrolamiento = a.codigo
    if a.datos:
        cfg.carpeta_datos = a.datos

    agente = AgenteSentinela(cfg)
    if a.una_vez:
        if not agente.cliente.token:
            agente.enrolar(cfg.codigo_enrolamiento)
        agente.ciclo_reporte()
        for hilo in agente.ciclo_comandos():
            hilo.join()
        return
    try:
        agente.iniciar()
    except KeyboardInterrupt:
        agente.detener()


if __name__ == "__main__":
    main()
