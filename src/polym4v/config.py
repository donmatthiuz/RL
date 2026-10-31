"""Configuración local; los secretos se excluyen de la representación."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Self

from dotenv import dotenv_values
from polymarket import ApiKeyCreds


class ConfigurationError(ValueError):
    """Configuración incompleta para conectarse a una cuenta."""


@dataclass(frozen=True)
class PolymarketSettings:
    private_key: str | None = field(default=None, repr=False)
    wallet_address: str | None = None
    api_key: str | None = field(default=None, repr=False)
    api_secret: str | None = field(default=None, repr=False)
    api_passphrase: str | None = field(default=None, repr=False)

    @classmethod
    def from_env(cls, env_file: str | Path = ".env") -> Self:
        """Lee .env sin modificar os.environ; el entorno tiene prioridad."""
        values = {**dotenv_values(env_file, interpolate=False), **os.environ}

        def read(name: str) -> str | None:
            value = values.get(name)
            if value is None:
                return None
            return value.strip() or None

        return cls(
            private_key=read("POLYMARKET_PRIVATE_KEY"),
            wallet_address=read("POLYMARKET_WALLET_ADDRESS"),
            api_key=read("POLYMARKET_API_KEY"),
            api_secret=read("POLYMARKET_API_SECRET"),
            api_passphrase=read("POLYMARKET_API_PASSPHRASE"),
        )

    def validate_authentication(self) -> None:
        """Comprueba los campos requeridos antes de hacer peticiones."""
        if not self.private_key:
            raise ConfigurationError(
                "Configura POLYMARKET_PRIVATE_KEY para usar una cuenta."
            )
        if not self.wallet_address:
            raise ConfigurationError(
                "Configura POLYMARKET_WALLET_ADDRESS con la dirección de tu cuenta."
            )
        credentials = (self.api_key, self.api_secret, self.api_passphrase)
        if any(credentials) and not all(credentials):
            raise ConfigurationError(
                "Configura juntas POLYMARKET_API_KEY, POLYMARKET_API_SECRET y "
                "POLYMARKET_API_PASSPHRASE, o deja las tres vacías."
            )

    def get_credentials(self) -> ApiKeyCreds | None:
        """Construye las credenciales L2; None permite derivarlas con el SDK."""
        self.validate_authentication()
        if self.api_key and self.api_secret and self.api_passphrase:
            return ApiKeyCreds(
                apiKey=self.api_key,
                secret=self.api_secret,
                passphrase=self.api_passphrase,
            )
        return None
