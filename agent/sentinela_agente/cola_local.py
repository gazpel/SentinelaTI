"""ColaLocalLecturas (L4, decisión D5) — RNF04: sin conexión se guardan al menos 72 h de lecturas
y se reenvían en orden cronológico, sin pérdidas ni duplicados.

Usa SQLite (incluido en Python): no hay que instalar nada en el equipo.
"""
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .modelo import Lectura


class ColaLocalLecturas:
    def __init__(self, ruta: Path | str, retencion_horas: int = 72):
        self.retencion = timedelta(hours=retencion_horas)
        self._bd = sqlite3.connect(str(ruta), check_same_thread=False)
        self._bd.execute("""CREATE TABLE IF NOT EXISTS lecturas_pendientes (
                                marca_tiempo TEXT PRIMARY KEY,   -- evita duplicados en la cola
                                contenido    TEXT NOT NULL)""")
        self._bd.commit()

    def encolar(self, l: Lectura) -> None:
        self._bd.execute("INSERT OR IGNORE INTO lecturas_pendientes VALUES (?, ?)",
                         (l.marca_tiempo.isoformat(), json.dumps(l.a_json())))
        self._bd.commit()
        self._depurar()

    def pendientes(self) -> list[Lectura]:
        filas = self._bd.execute("SELECT contenido FROM lecturas_pendientes ORDER BY marca_tiempo").fetchall()
        return [Lectura.desde_json(json.loads(f[0])) for f in filas]

    def confirmar_envio(self, l: Lectura) -> None:
        self._bd.execute("DELETE FROM lecturas_pendientes WHERE marca_tiempo = ?", (l.marca_tiempo.isoformat(),))
        self._bd.commit()

    def cantidad(self) -> int:
        return self._bd.execute("SELECT COUNT(*) FROM lecturas_pendientes").fetchone()[0]

    def _depurar(self) -> None:
        """Descarta lo más antiguo que la ventana de retención (como mínimo 72 h)."""
        limite = (datetime.now(timezone.utc) - self.retencion).isoformat()
        self._bd.execute("DELETE FROM lecturas_pendientes WHERE marca_tiempo < ?", (limite,))
        self._bd.commit()

    def cerrar(self) -> None:
        self._bd.close()
