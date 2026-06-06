#!/usr/bin/env python3
"""Dashboard account management (password + TOTP secret).

Usage:
    python scripts/manage.py useradd <username>
    python scripts/manage.py passwd  <username>
    python scripts/manage.py list
    python scripts/manage.py delete  <username>

The TOTP secret is generated randomly and printed as an otpauth:// URI plus
an ASCII QR code to scan with Google Authenticator / Aegis / etc.
"""

from __future__ import annotations

import getpass
import json
import sys
from pathlib import Path

# Allow importing the app/ package from the project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pyotp  # noqa: E402
import qrcode  # noqa: E402

from app.auth import hash_password  # noqa: E402
from app.config import settings  # noqa: E402

ISSUER = "Tor Relay Dashboard"


def _load() -> dict:
    try:
        return json.loads(settings.users_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save(users: dict) -> None:
    settings.users_path.write_text(
        json.dumps(users, indent=2), encoding="utf-8"
    )
    try:
        settings.users_path.chmod(0o600)
    except OSError:
        pass


def _ask_password() -> str:
    while True:
        p1 = getpass.getpass("Password: ")
        if len(p1) < 10:
            print("  -> 10 characters minimum.")
            continue
        p2 = getpass.getpass("Confirm : ")
        if p1 != p2:
            print("  -> passwords differ.")
            continue
        return p1


def _print_totp(username: str, secret: str) -> None:
    uri = pyotp.TOTP(secret).provisioning_uri(name=username, issuer_name=ISSUER)
    print("\nTOTP secret:", secret)
    print("otpauth URI:", uri)
    print("\nScan this QR code in your 2FA app:\n")
    qr = qrcode.QRCode(border=1)
    qr.add_data(uri)
    qr.make(fit=True)
    qr.print_ascii(invert=True)


def cmd_useradd(username: str) -> None:
    users = _load()
    if username in users:
        print(f'User "{username}" already exists.')
        sys.exit(1)
    password = _ask_password()
    secret = pyotp.random_base32()
    users[username] = {
        "password_hash": hash_password(password),
        "totp_secret": secret,
    }
    _save(users)
    print(f'\n✔ User "{username}" created in {settings.users_path}')
    _print_totp(username, secret)


def cmd_passwd(username: str) -> None:
    users = _load()
    if username not in users:
        print(f"Unknown user: {username}")
        sys.exit(1)
    users[username]["password_hash"] = hash_password(_ask_password())
    _save(users)
    print("✔ Password updated.")


def cmd_list() -> None:
    users = _load()
    if not users:
        print("No users.")
        return
    for name in users:
        print(" -", name)


def cmd_delete(username: str) -> None:
    users = _load()
    if users.pop(username, None) is None:
        print(f"Unknown user: {username}")
        sys.exit(1)
    _save(users)
    print(f'✔ User "{username}" deleted.')


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)
    cmd, *rest = args
    if cmd == "useradd" and rest:
        cmd_useradd(rest[0])
    elif cmd == "passwd" and rest:
        cmd_passwd(rest[0])
    elif cmd == "list":
        cmd_list()
    elif cmd == "delete" and rest:
        cmd_delete(rest[0])
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
