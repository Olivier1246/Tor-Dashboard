#!/usr/bin/env bash
# ===========================================================================
# Install the Tor Relay Dashboard on Debian/Ubuntu.
# Run as root (sudo) on the VM. As idempotent as possible.
# ===========================================================================
set -euo pipefail

APP_DIR="/opt/tor-dashboard"
APP_USER="tordash"
HELPER="/usr/local/bin/tor-dashboard-helper"
SRC="$(cd "$(dirname "$0")/.." && pwd)"

[ "$(id -u)" -eq 0 ] || { echo "Run as root (sudo)." >&2; exit 1; }

echo "==> System packages"
apt-get update -qq
apt-get install -y python3 python3-venv python3-pip tor

echo "==> Service user: $APP_USER"
id "$APP_USER" &>/dev/null || useradd --system --create-home \
  --home-dir "/home/$APP_USER" --shell /usr/sbin/nologin "$APP_USER"
# Access to the ControlPort authentication cookie
usermod -aG debian-tor "$APP_USER"
# Read access to the Tor journal (DoS / heartbeat stats on the Security panel)
usermod -aG systemd-journal "$APP_USER"

echo "==> Copying the application into $APP_DIR"
mkdir -p "$APP_DIR"
cp -r "$SRC/app" "$SRC/scripts" "$SRC/requirements.txt" "$APP_DIR/"
[ -f "$APP_DIR/.env" ] || cp "$SRC/.env.example" "$APP_DIR/.env"

echo "==> Python virtual environment"
python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --quiet --upgrade pip
"$APP_DIR/.venv/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"

echo "==> Privileged helper"
install -o root -g root -m 0755 "$SRC/deploy/tor-dashboard-helper" "$HELPER"
mkdir -p /etc/tor-dashboard
[ -f /etc/tor-dashboard/helper.conf ] || \
  install -o root -g root -m 0644 "$SRC/deploy/helper.conf.example" \
  /etc/tor-dashboard/helper.conf

echo "==> sudoers rule"
install -o root -g root -m 0440 "$SRC/deploy/sudoers-tor-dashboard" \
  /etc/sudoers.d/tor-dashboard
visudo -cf /etc/sudoers.d/tor-dashboard

echo "==> Permissions"
chown -R "$APP_USER:$APP_USER" "$APP_DIR"
chmod 600 "$APP_DIR/.env"

echo "==> Session secret key"
if grep -q '^SECRET_KEY=change-me' "$APP_DIR/.env"; then
  KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
  sed -i "s|^SECRET_KEY=.*|SECRET_KEY=${KEY}|" "$APP_DIR/.env"
  echo "    key generated automatically."
fi

echo "==> systemd service"
install -o root -g root -m 0644 "$SRC/deploy/tor-dashboard.service" \
  /etc/systemd/system/tor-dashboard.service
systemctl daemon-reload
systemctl enable tor-dashboard.service

cat <<EOF

----------------------------------------------------------------------------
Installation complete. Remaining steps:

  1. Enable ControlPort + onion service in the torrc:
       sudo cat $SRC/deploy/torrc.example >> /etc/tor/torrc
       sudo systemctl restart tor@default
     (adapt the relay values to your configuration)

  2. Create an administrator account (password + 2FA):
       sudo -u $APP_USER $APP_DIR/.venv/bin/python \\
            $APP_DIR/scripts/manage.py useradd admin
     -> scan the QR code in your TOTP app.

  3. Start the dashboard:
       sudo systemctl start tor-dashboard

  4. Get the dashboard .onion address:
       sudo cat /var/lib/tor/dashboard/hostname
     Open it in Tor Browser from anywhere.
----------------------------------------------------------------------------
EOF
