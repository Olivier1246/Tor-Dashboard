#!/usr/bin/env bash
# ===========================================================================
# Installation du Tor Relay Dashboard sur Debian/Ubuntu.
# À exécuter en root (sudo) sur la VM. Idempotent autant que possible.
# ===========================================================================
set -euo pipefail

APP_DIR="/opt/tor-dashboard"
APP_USER="tordash"
HELPER="/usr/local/bin/tor-dashboard-helper"
SRC="$(cd "$(dirname "$0")/.." && pwd)"

[ "$(id -u)" -eq 0 ] || { echo "À lancer en root (sudo)." >&2; exit 1; }

echo "==> Paquets système"
apt-get update -qq
apt-get install -y python3 python3-venv python3-pip tor

echo "==> Utilisateur de service : $APP_USER"
id "$APP_USER" &>/dev/null || useradd --system --create-home \
  --home-dir "/home/$APP_USER" --shell /usr/sbin/nologin "$APP_USER"
# Accès au cookie d'authentification du ControlPort
usermod -aG debian-tor "$APP_USER"

echo "==> Copie de l'application dans $APP_DIR"
mkdir -p "$APP_DIR"
cp -r "$SRC/app" "$SRC/scripts" "$SRC/requirements.txt" "$APP_DIR/"
[ -f "$APP_DIR/.env" ] || cp "$SRC/.env.example" "$APP_DIR/.env"

echo "==> Environnement virtuel Python"
python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --quiet --upgrade pip
"$APP_DIR/.venv/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"

echo "==> Helper privilégié"
install -o root -g root -m 0755 "$SRC/deploy/tor-dashboard-helper" "$HELPER"
mkdir -p /etc/tor-dashboard
[ -f /etc/tor-dashboard/helper.conf ] || \
  install -o root -g root -m 0644 "$SRC/deploy/helper.conf.example" \
  /etc/tor-dashboard/helper.conf

echo "==> Règle sudoers"
install -o root -g root -m 0440 "$SRC/deploy/sudoers-tor-dashboard" \
  /etc/sudoers.d/tor-dashboard
visudo -cf /etc/sudoers.d/tor-dashboard

echo "==> Permissions"
chown -R "$APP_USER:$APP_USER" "$APP_DIR"
chmod 600 "$APP_DIR/.env"

echo "==> Clé secrète de session"
if grep -q '^SECRET_KEY=change-me' "$APP_DIR/.env"; then
  KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
  sed -i "s|^SECRET_KEY=.*|SECRET_KEY=${KEY}|" "$APP_DIR/.env"
  echo "    clé générée automatiquement."
fi

echo "==> Service systemd"
install -o root -g root -m 0644 "$SRC/deploy/tor-dashboard.service" \
  /etc/systemd/system/tor-dashboard.service
systemctl daemon-reload
systemctl enable tor-dashboard.service

cat <<EOF

----------------------------------------------------------------------------
Installation terminée. Étapes restantes :

  1. Activez ControlPort + onion service dans le torrc :
       sudo cat $SRC/deploy/torrc.example >> /etc/tor/torrc
       sudo systemctl restart tor@default
     (adaptez les valeurs de relais à votre configuration)

  2. Créez un compte administrateur (mot de passe + 2FA) :
       sudo -u $APP_USER $APP_DIR/.venv/bin/python \\
            $APP_DIR/scripts/manage.py useradd admin
     → scannez le QR code dans votre application TOTP.

  3. Démarrez le dashboard :
       sudo systemctl start tor-dashboard

  4. Récupérez l'adresse .onion du dashboard :
       sudo cat /var/lib/tor/dashboard/hostname
     Ouvrez-la dans Tor Browser depuis n'importe où.
----------------------------------------------------------------------------
EOF
