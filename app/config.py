"""Chargement de la configuration depuis l'environnement / .env."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Sécurité / sessions
    secret_key: str = "change-me"
    cookie_secure: bool = False
    session_max_age: int = 3600

    # Serveur web
    host: str = "127.0.0.1"
    port: int = 8080

    # ControlPort Tor
    tor_control_port: int = 9051
    tor_control_password: str = ""

    # Contrôle système
    tor_service: str = "tor@default"
    torrc_path: str = "/etc/tor/torrc"
    helper_path: str = "/usr/local/bin/tor-dashboard-helper"
    onion_hostname_file: str = "/var/lib/tor/dashboard/hostname"

    # Utilisateurs
    users_file: str = "users.json"

    # Historique persistant
    history_db: str = "history.db"
    sample_interval: int = 60          # secondes entre deux échantillons
    history_retention_days: int = 7    # purge au-delà

    @property
    def users_path(self) -> Path:
        p = Path(self.users_file)
        return p if p.is_absolute() else BASE_DIR / p

    @property
    def history_path(self) -> Path:
        p = Path(self.history_db)
        return p if p.is_absolute() else BASE_DIR / p


settings = Settings()
