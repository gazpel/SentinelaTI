"""AlmacenToken (L4, decisión D3).

En el prototipo el token se guarda en un archivo de la carpeta de datos del
agente. Pendiente L6: cifrarlo con DPAPI y restringir la carpeta a la cuenta
del servicio (RNF02).
"""
from pathlib import Path


class AlmacenToken:
    def __init__(self, carpeta: Path):
        self.ruta = Path(carpeta) / "token_agente.txt"

    def guardar(self, t: str) -> None:
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        self.ruta.write_text(t, encoding="utf-8")

    def leer(self) -> str | None:
        if self.ruta.exists():
            return self.ruta.read_text(encoding="utf-8").strip() or None
        return None

    def borrar(self) -> None:
        self.ruta.unlink(missing_ok=True)
