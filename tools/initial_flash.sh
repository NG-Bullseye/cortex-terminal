#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════
# tools/initial_flash.sh — Preflight-Gate fuer den EINMALIGEN USB-Flash
# ────────────────────────────────────────────────────────────────────
# Faengt genau die Fehlerquellen ab, an denen der Initial-Flash scheitert
# (fehlende secrets/env, kein dialout, kein/mehrere USB-Ports), zeigt
# Geraet + IP zur Bestaetigung und ruft dann erst `esphome run`.
# Das ist KEIN Durchreicher: ohne diese Checks flasht man blind und
# debuggt hinterher kryptische ESPHome-Fehler.
#
# Nur fuer den ERSTEN Flash eines Displays. Danach OTA via README.
#
# Usage:  ./tools/initial_flash.sh <device-file.yaml> [/dev/ttyUSBx]
# ════════════════════════════════════════════════════════════════════
set -euo pipefail

cd "$(dirname "$0")/.."   # immer aus Repo-Root arbeiten

die() { echo "FEHLER: $*" >&2; exit 1; }

# ── Argument: Device-File ────────────────────────────────────────────
DEVICE_FILE="${1:-}"
[ -n "$DEVICE_FILE" ] || die "Kein Device-File. Usage: $0 <device-file.yaml> [/dev/ttyUSBx]"
[ -f "$DEVICE_FILE" ] || die "Device-File '$DEVICE_FILE' nicht gefunden (im Repo-Root?)."

# ── Preflight: Werkzeug + Credentials ────────────────────────────────
command -v esphome >/dev/null || die "esphome nicht installiert → pip install --user esphome"
[ -f secrets.yaml ] || die "secrets.yaml fehlt (api_key + ota_password) → siehe INITIAL_FLASH.md §2b"
: "${ESPHOME_WIFI_SSID:?WLAN-Env fehlt → export ESPHOME_WIFI_SSID=... (INITIAL_FLASH.md §2c)}"
: "${ESPHOME_WIFI_PASSWORD:?WLAN-Env fehlt → export ESPHOME_WIFI_PASSWORD=... (INITIAL_FLASH.md §2c)}"
groups | grep -qw dialout || die "Nicht in Gruppe 'dialout' → sudo usermod -aG dialout \$USER, dann neu einloggen"

# ── IP/Hostname aus dem Device-File ziehen (zur Kontrolle anzeigen) ───
STATIC_IP=$(grep -E '^\s*static_ip:'   "$DEVICE_FILE" | head -1 | sed -E 's/.*static_ip:\s*([0-9.]+).*/\1/')
HOSTNAME=$( grep -E '^\s*device_name:' "$DEVICE_FILE" | head -1 | sed -E 's/.*device_name:\s*([^ #]+).*/\1/')
[ -n "$STATIC_IP" ] || die "Keine static_ip im Device-File gefunden — substitutions kaputt?"

# ── Seriellen Port bestimmen (Arg gewinnt, sonst Auto-Detect) ────────
PORT="${2:-}"
if [ -z "$PORT" ]; then
  mapfile -t PORTS < <(ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null || true)
  case "${#PORTS[@]}" in
    0) die "Kein /dev/ttyUSB*|ttyACM* gefunden. Display per USB-DATENkabel anstecken (INITIAL_FLASH.md §3).";;
    1) PORT="${PORTS[0]}";;
    *) die "Mehrere Ports gefunden (${PORTS[*]}). Eindeutig machen oder Port als 2. Argument uebergeben.";;
  esac
fi
[ -e "$PORT" ] || die "Port '$PORT' existiert nicht."

# ── Bestaetigung (kein blindes Flashen) ──────────────────────────────
cat <<EOF

  ── INITIAL USB-FLASH ────────────────────────────────
   Device-File : $DEVICE_FILE
   Hostname    : ${HOSTNAME:-?}   (wird fix vergeben, NICHT umbenennen)
   statische IP: $STATIC_IP   (wird ins Geraet gebrannt)
   USB-Port    : $PORT
  ─────────────────────────────────────────────────────
  Danach laeuft das Display fix unter $STATIC_IP → ab dann nur OTA.
EOF
read -r -p "  Flashen? [y/N] " ans
[ "$ans" = "y" ] || [ "$ans" = "Y" ] || die "Abgebrochen."

# ── Flash (USB) + Live-Log ───────────────────────────────────────────
exec esphome run "$DEVICE_FILE" --device "$PORT"
