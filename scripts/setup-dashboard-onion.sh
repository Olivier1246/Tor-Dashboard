#!/usr/bin/env bash
# ===========================================================================
# Move the dashboard onion service into its OWN Tor instance (tor@dashboard).
#
# Why: running a relay AND a hidden service in the same Tor process triggers
# the warning "That's not very secure" (tpo/core/tor/8742). This script splits
# them: the relay stays in tor@default, the dashboard onion moves to a separate
# tor@dashboard instance running as its own user (_tor-dashboard).
#
# It is idempotent and preserves the existing .onion address if present.
# Run as root (sudo) on the VM, from the project root:
#     sudo ./scripts/setup-dashboard-onion.sh
# ===========================================================================
set -euo pipefail

INSTANCE="dashboard"
INST_USER="_tor-${INSTANCE}"
INST_DATADIR="/var/lib/tor-instances/${INSTANCE}"
INST_TORRC="/etc/tor/instances/${INSTANCE}/torrc"
HS_DIR="${INST_DATADIR}/dashboard_onion"
OLD_HS_DIR="/var/lib/tor/dashboard"          # old location (inside tor@default)
MAIN_TORRC="/etc/tor/torrc"
APP_DIR="/opt/tor-dashboard"
APP_USER="tordash"
DROPIN="/etc/systemd/system/tor-dashboard.service.d/onion-instance.conf"

[ "$(id -u)" -eq 0 ] || { echo "Run as root (sudo)." >&2; exit 1; }
command -v tor-instance-create >/dev/null || {
  echo "tor-instance-create not found (install the 'tor' package)." >&2; exit 1; }

echo "==> 1/7 Creating the tor@${INSTANCE} instance"
if [ ! -d "/etc/tor/instances/${INSTANCE}" ]; then
  tor-instance-create "$INSTANCE"
else
  echo "    instance already exists, reusing it."
fi

echo "==> 2/7 Writing ${INST_TORRC}"
cat > "$INST_TORRC" <<EOF
# Dashboard onion service — dedicated Tor instance (no relay here).
SocksPort 0
HiddenServiceDir ${HS_DIR}/
HiddenServiceDirGroupReadable 1
HiddenServicePort 80 127.0.0.1:8080
HiddenServiceVersion 3
EOF

echo "==> 3/7 Migrating onion keys (to preserve the .onion address)"
install -d -o "$INST_USER" -g "$INST_USER" -m 0700 "$HS_DIR"
if [ -f "${OLD_HS_DIR}/hs_ed25519_secret_key" ]; then
  cp -a "${OLD_HS_DIR}/hs_ed25519_secret_key" \
        "${OLD_HS_DIR}/hs_ed25519_public_key" \
        "${OLD_HS_DIR}/hostname" "$HS_DIR/" 2>/dev/null || true
  chown -R "$INST_USER:$INST_USER" "$HS_DIR"
  echo "    existing keys migrated — same .onion will be kept."
else
  echo "    no existing keys found — a new .onion will be generated."
fi

echo "==> 4/7 Disabling the onion service in the relay torrc (${MAIN_TORRC})"
if grep -qE '^\s*HiddenService' "$MAIN_TORRC"; then
  cp -a "$MAIN_TORRC" "${MAIN_TORRC}.bak.$(date +%s)"
  sed -i -E 's/^(\s*)(HiddenService(Dir|Port|Version|DirGroupReadable)\b)/\1#\2/' "$MAIN_TORRC"
  echo "    HiddenService* lines commented out (backup saved)."
else
  echo "    no active HiddenService line in the relay torrc, nothing to do."
fi

echo "==> 5/7 Granting ${APP_USER} read access to the new onion dir"
usermod -aG "$INST_USER" "$APP_USER"

echo "==> 6/7 Pointing the dashboard at the new hostname file"
if [ -f "${APP_DIR}/.env" ]; then
  if grep -q '^ONION_HOSTNAME_FILE=' "${APP_DIR}/.env"; then
    sed -i "s#^ONION_HOSTNAME_FILE=.*#ONION_HOSTNAME_FILE=${HS_DIR}/hostname#" "${APP_DIR}/.env"
  else
    echo "ONION_HOSTNAME_FILE=${HS_DIR}/hostname" >> "${APP_DIR}/.env"
  fi
fi
# systemd drop-in: add the instance group + ordering to the dashboard service
mkdir -p "$(dirname "$DROPIN")"
cat > "$DROPIN" <<EOF
[Unit]
After=tor@${INSTANCE}.service
Wants=tor@${INSTANCE}.service

[Service]
SupplementaryGroups=${INST_USER}
EOF

echo "==> 7/7 Restarting services"
systemctl daemon-reload
systemctl restart "tor@default"
systemctl enable --now "tor@${INSTANCE}"
sleep 2
systemctl restart tor-dashboard || true

echo
echo "----------------------------------------------------------------------------"
echo "Done. The dashboard onion now runs in tor@${INSTANCE} (user ${INST_USER})."
echo "Relay + hidden-service warning is gone from tor@default."
echo
echo "Onion address:"
cat "${HS_DIR}/hostname" 2>/dev/null || echo "  (starting up — check again in a few seconds)"
echo "----------------------------------------------------------------------------"
