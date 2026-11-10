"""Rutas del proyecto. Cada máquina puede moverlas con variables de entorno o con .env.

Por defecto todo vive bajo la raíz del repositorio. Las variables del entorno tienen
prioridad sobre .env, y .env no modifica os.environ.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values


@dataclass(frozen=True)
class Paths:
    root: Path
    data: Path
    models: Path
    reports: Path

    @property
    def raw(self) -> Path:
        return self.data / "raw"

    @property
    def processed(self) -> Path:
        return self.data / "processed"

    @property
    def offline(self) -> Path:
        return self.data / "offline"

    @property
    def configs(self) -> Path:
        return self.root / "configs"


def get_paths(env_file: str | Path = ".env", root: str | Path | None = None) -> Paths:
    """Resuelve las rutas; las relativas se interpretan desde la raíz."""
    values = {**dotenv_values(env_file, interpolate=False), **os.environ}

    def read(name: str, default: Path, base: Path) -> Path:
        value = (values.get(name) or "").strip()
        if not value:
            return default
        path = Path(value)
        return path if path.is_absolute() else base / path

    cwd = Path.cwd()
    base = Path(root) if root is not None else read("POLYM4V_ROOT", cwd, cwd)
    return Paths(
        root=base,
        data=read("POLYM4V_DATA_DIR", base / "data", base),
        models=read("POLYM4V_MODELS_DIR", base / "models", base),
        reports=read("POLYM4V_REPORTS_DIR", base / "reports", base),
    )
