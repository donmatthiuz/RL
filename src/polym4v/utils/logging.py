"""Logging del paquete: un solo handler y nivel tomado de POLYM4V_LOG_LEVEL."""

import logging
import os

_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def get_logger(name: str) -> logging.Logger:
    """Devuelve un logger bajo 'polym4v'; configurar dos veces no duplica la salida."""
    package = logging.getLogger("polym4v")
    if not package.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(_FORMAT))
        package.addHandler(handler)
    package.setLevel(os.environ.get("POLYM4V_LOG_LEVEL", "INFO").upper())
    return logging.getLogger(name)
