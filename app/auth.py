"""Authentification : mot de passe (bcrypt) + double facteur TOTP.

Les comptes sont stockés dans un fichier JSON (``users_file``) :

    {
      "admin": {
        "password_hash": "$2b$...",
        "totp_secret": "BASE32SECRET"
      }
    }
"""

from __future__ import annotations

import json
from typing import Any

import bcrypt
import pyotp
from fastapi import Request
from fastapi.responses import RedirectResponse

from .config import settings


def _load_users() -> dict[str, Any]:
    try:
        with open(settings.users_path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_credentials(username: str, password: str, totp_code: str) -> bool:
    """Vérifie identifiant + mot de passe + code TOTP (les trois)."""
    users = _load_users()
    user = users.get(username)
    if not user:
        # Comparaison factice pour limiter l'oracle temporel
        bcrypt.checkpw(b"x", bcrypt.gensalt())
        return False

    pw_ok = bcrypt.checkpw(
        password.encode(), user["password_hash"].encode()
    )
    secret = user.get("totp_secret")
    totp_ok = bool(secret) and pyotp.TOTP(secret).verify(
        (totp_code or "").strip(), valid_window=1
    )
    return pw_ok and totp_ok


def current_user(request: Request) -> str | None:
    return request.session.get("user")


def require_auth(request: Request):
    """Dépendance FastAPI : redirige vers /login si non authentifié.

    Lève une RedirectResponse via exception gérée dans main (voir
    ``redirect_unauthenticated``). On renvoie ici l'utilisateur si connecté.
    """
    user = current_user(request)
    if not user:
        raise NotAuthenticated()
    return user


class NotAuthenticated(Exception):
    """Levée quand une route protégée est atteinte sans session valide."""


def login_redirect() -> RedirectResponse:
    return RedirectResponse(url="/login", status_code=303)
