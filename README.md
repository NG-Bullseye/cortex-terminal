# cortex-terminal — CYD-Panel (ESPHome, ESP32)

**Was:** ESP32-basiertes CYD (Cheap Yellow Display, 240×320 TFT mit Touch). Hardware-Frontend fuer das Cortex-Smarthome-System. Zeigt Status, hat Touch-Buttons fuer Smart-Home-Aktionen, sendet HTTP-Requests an Cortex/HA.

**Wofuer:** „Cortex Terminal" am PC-Tisch — Touch-Buttons triggern HA-Scripts (`script.turn_on`), Cortex-Aktionen (`/api/feed`, `/api/sync_to_vibe`, `/api/blackout`), und zeigt Feed/Status-Updates.

---

## Multidisplay-Architektur

Dieses Repo betreibt **mehrere CYD-Displays**, jedes mit eigenem UI. Gemeinsame Plattform liegt in `common/`, jedes Display ist eine duenne Device-YAML im Repo-Root.

```
common/hardware.yaml   Chip, WiFi(${static_ip}), API/OTA, SPI/Display/Touch, Outputs, Sensoren
common/ui_base.yaml    Fonts + LVGL-Basis + Style-Definitionen
cortex-terminal.yaml   Display: Haupt-Panel  (Hostname cyd-panel, .240) — voller UI
cortex-vvo.yaml        Display: Zweitdisplay (Hostname cortex-vvo, .241) — CTRL2-Spiegel
displays.yaml          Registry: NAME -> IP -> Device-File
```

Ein Device-File = `substitutions` (device_name/static_ip) + `packages:` (zieht common) + eigene `lvgl.pages` (+ optional Globals/Intervals/text_sensors). Die Plattform-Boilerplate steht nur einmal in `common/`.

**Identitaet:** Der Firmware-`name` ist zugleich der Hostname und wird beim Initial-Flash fix vergeben + in HA gepairt → **nie umbenennen**. Darum heisst das Haupt-Panel firmware-seitig weiter `cyd-panel`, obwohl die Device-Datei `cortex-terminal.yaml` heisst.

### Display hinzufuegen

1. **Freie IP** gegen `~/cortex/docs/network-devices.md` pruefen, dort eintragen.
2. **`displays.yaml`** um einen Eintrag (name → file/hostname/ip/role) erweitern.
3. **`<name>.yaml`** im Root anlegen:
   ```yaml
   substitutions:
     device_name: <hostname>      # == displays.yaml
     static_ip: 192.168.1.<x>     # == displays.yaml
   esphome:
     name: ${device_name}
     friendly_name: "<Anzeigename>"
   packages:
     hardware: !include common/hardware.yaml
     ui_base: !include common/ui_base.yaml
   lvgl:
     pages:
       - id: page_main
         widgets: [ ... ]         # eigenes UI
   ```
4. **Compile-Check** (kein Flash): `esphome compile <name>.yaml`.
5. **Initial-Flash** (einmalig per USB, vergibt IP + paired HA): `esphome run <name>.yaml --device /dev/ttyUSB0`, danach OTA via `--device <ip>`. **Idiotensichere Schritt-fuer-Schritt-Anleitung inkl. Preflight-Helper (`tools/initial_flash.sh`) und Troubleshooting → `INITIAL_FLASH.md`.**

---

## Hardware

- **Chip:** ESP32 (`esp32dev`, Arduino-Framework via ESPHome)
- **Hostname:** `cyd-panel`
- **IP (statisch):** `192.168.1.240`
- **MAC:** `b0:cb:d8:da:b9:ec`
- **Display:** 240×320 ILI9341 TFT, SPI Bus 1
- **Touch:** XPT2046, SPI Bus 2
- **Web-Server:** Port 80 (MCP-Endpoint)

Pinout-Details: siehe `cortex-terminal.yaml` Sektion „SPI Buses" + Display/Touch-Configs. CYD-Boards haben fixed Pinout — nicht aendern ohne Hardware-Doku.

---

## Live-Verhalten

- **Boot:** verbindet WiFi → API → Web-Server. Kein Boot-Sync wie bei BT-Volume.
- **Touch:** registriert Tap-Events, fuehrt konfigurierte HTTP-Calls zu Cortex/HA aus.
- **HA-Integration:** entry_id `01KM8CGFCPBJYSX5JT0S2PV1X6`, Port 6053, Noise-encrypted.
- **HTTP-Endpoints (incoming):** Cortex/HA pushen Feed-Updates an `http://192.168.1.240/...` (siehe Web-Server-Config).

---

## Backbone

```
Touch am CYD
    │
    ▼
ESPHome on_press handler
    │   http_request.post(...)
    ▼
HA / Cortex (192.168.1.225)
    │
    ▼  (HA-Side: ESPHome-Integration zeigt Touch-State,
    │   Cortex-Side: HTTP-Endpoint feedback)
    ▼
zurueck zum Panel via Push (HTTP)
```

---

## Quickstart fuer User

```bash
cd ~/esp_repos/cortex-terminal

# YAML-Aenderung
$EDITOR cortex-terminal.yaml

# OTA-Flash + Live-Log
esphome run cortex-terminal.yaml --device 192.168.1.240
```

---

## Deploy-Pipeline (Schritt fuer Schritt)

### Vorbedingungen (one-time)

1. `esphome` CLI: `which esphome` → `/home/leona/.local/bin/esphome`. Install: `pip install --user esphome`.
2. `secrets.yaml` in diesem Repo (gitignored). Enthaelt mindestens:
   ```yaml
   api_key:      "<base64 32-byte key>"
   ota_password: "<your-ota-password>"
   ```
   WiFi-Credentials werden hier ueber Env-Vars `ESPHOME_WIFI_SSID` / `ESPHOME_WIFI_PASSWORD` gezogen (siehe `cortex-terminal.yaml`) — die muessen vor `esphome run` exportiert sein:
   ```bash
   export ESPHOME_WIFI_SSID="..."
   export ESPHOME_WIFI_PASSWORD="..."
   ```
3. `protobuf` Python-Modul: `python3 -c "import google.protobuf"`. Bei Fail: `pip install --user --break-system-packages protobuf`.

### Deploy-Schritt 1 — YAML-Aenderung

YAML editieren in `cortex-terminal.yaml`. Touch-Layouts und HTTP-Calls sind in den Kommentaren markiert (siehe `BUTTONS.md`, `NEW_BUTTON_WORKFLOW.md`).

### Deploy-Schritt 2 — OTA-Flash

```bash
cd ~/esp_repos/cortex-terminal
esphome run cortex-terminal.yaml --device 192.168.1.240
```

Erwarteter Log:
```
INFO Successfully compiled program.
INFO Connecting to 192.168.1.240 port 8266...
INFO OTA successful
INFO Successful handshake with cyd-panel @ 192.168.1.240
[I][app:215]: ESPHome version X.Y.Z compiled on ...
```

### Deploy-Schritt 3 — Verifikation

```bash
TOKEN="<HA-Token>"

# Entity available?
curl -s -H "Authorization: Bearer $TOKEN" \
     "http://192.168.1.225:8123/api/states/<eine-entity-vom-cyd>" | python3 -m json.tool

# Web-Server reachable?
curl -s http://192.168.1.240/ | head
```

### Deploy-Schritt 4 — HITL-Verifikation

User testet:
- Display zeigt erwartete Inhalte
- Touch-Buttons reagieren physisch (richtiger Pressure-Punkt, kein versehentliches Triggern)
- HA-Scripts/Cortex-Endpoints werden bei Touch ausgeloest

---

## USB-Recovery

Nur wenn OTA failed (api_key drift, Crash-Loop, etc.):

```bash
ls -la /dev/ttyUSB*
esphome run cortex-terminal.yaml --device /dev/ttyUSB0
```

USB-Flash setzt Geraet auf aktuellen `secrets.yaml api_key` zurueck. Anschliessend ggf. HA-Integration-Reload.

---

## Secrets-Management

Datei: `secrets.yaml` (gitignored).

```yaml
api_key:      "<base64 32-byte>"
ota_password: "<password>"
```

WiFi-Credentials separat ueber Env-Vars (siehe oben).

### Pitfall — api_key-Drift

Wenn `secrets.yaml.api_key` veraendert wird ohne sofortigen Re-Flash → ESP behaelt alten Key, HA hat neuen → API-Connection schlaegt still fehl, Entity `unavailable`.

**Pflicht:** Bei `secrets.yaml`-Aenderung sofort flashen + HA-Reload.

```bash
# Backup vorher
cp secrets.yaml secrets.yaml.bak-$(date +%F)
# Aenderung
$EDITOR secrets.yaml
# Flash
esphome run cortex-terminal.yaml --device 192.168.1.240   # oder USB falls Key-Drift OTA blockiert
# HA-Reload
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
     http://192.168.1.225:8123/api/config/config_entries/entry/01KM8CGFCPBJYSX5JT0S2PV1X6/reload
```

---

## Diagnose-Tree

### Symptom A — HA-Entity `unavailable`

```bash
ping -c 2 192.168.1.240                                      # Host alive?
timeout 2 bash -c 'cat < /dev/tcp/192.168.1.240/6053'        # API port open? (exit 124 = ok)
esphome logs cortex-terminal.yaml --device 192.168.1.240           # Handshake?
grep noise_psk /home/leona/homeassistant/_data/.storage/core.config_entries | grep cyd-panel
# Mismatch zu secrets.yaml api_key → key drift → Pfad: USB-Flash + HA-Reload
```

HA-Reload:
```bash
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
     http://192.168.1.225:8123/api/config/config_entries/entry/01KM8CGFCPBJYSX5JT0S2PV1X6/reload
```

### Symptom B — Display tot / Touch reagiert nicht

1. Reboot (Power-Cycle).
2. Verkabelung pruefen (USB-Stromversorgung stabil? Kein Brownout?).
3. Im Log: `[E][component:582] Components should block for at most 30 ms` haeufig → blockierende Lambdas reduzieren.
4. Touch-Kalibrierung in YAML pruefen.

### Symptom C — HTTP-Calls an Cortex/HA failen

```
[E][http_request.idf:216]: HTTP Request failed; URL: ...; Code: 404
```

→ Cortex-Endpoint existiert nicht / ist nicht gestartet. Cortex-Container checken:
```bash
docker compose -f ~/cortex/docker-compose.yml ps
```

---

## Pitfalls

1. **WiFi-Credentials in Env-Vars** — vor `esphome run` exportieren, sonst Build-Fehler `Variable not defined`.
2. **CYD-Pinout ist fix** — nicht im YAML aendern ohne CYD-Hardware-Doku.
3. **Display-Init blockiert Boot ~3s** — Boot-Critical-Lambdas vermeiden, sonst Watchdog-Reset.
4. **HTTP-Request Timeout = 3s** — wenn Cortex langsam antwortet, Calls failen still. Timeout im YAML hochsetzen oder Cortex-Performance fixen.
5. **Touch-Debounce nicht vergessen** — sonst Triple-Triggers.
6. **`http_request:` consumes RAM** — bei vielen parallelen Calls OOM-Risiko (RAM ist knapp auf ESP32).
7. **`secrets.yaml` ist gitignored** — Backup ueber `secrets.yaml.bak-*` lokal + GDrive.

---

## Test-Verfahren

Siehe `testing.md` in diesem Repo. Pflicht-Run nach Aenderung:
1. OTA-Flash erfolgreich
2. Display zeigt erwartetes Layout
3. Jeder Touch-Button triggert die richtige Aktion
4. HTTP-Calls an Cortex landen (Cortex-Logs checken)

---

## Verwandte Repos

- `~/esp_repos/bt-volume-control/` — generelles ESPHome-Template (BT-Volume-Control)
- `~/esp_repos/bastion/` — anderes ESP32-Geraet (DNS-Adblocker, separates Subnet)
- `~/cortex/` — Cortex-Code, das die HTTP-Endpoints bereitstellt
- `~/homeassistant/_data/` — HA-Konfig

---

## Referenzen

- `cortex-terminal.yaml` — Device-File Haupt-Panel (ESPHome-Konfiguration)
- `cortex-vvo.yaml` — Device-File Zweitdisplay
- `common/hardware.yaml`, `common/ui_base.yaml` — geteilte Plattform-Packages
- `displays.yaml` — Display-Registry (NAME → IP)
- `INITIAL_FLASH.md` — einmaliger USB-Erst-Flash (Port, statische IP, Verify, OTA-Umstieg)
- `tools/initial_flash.sh` — Preflight-Gate + Auto-Port-Detection fuer den Initial-Flash
- `BUTTONS.md` — Layout der Touch-Buttons
- `NEW_BUTTON_WORKFLOW.md` — wie ein neuer Touch-Button hinzugefuegt wird
- `secrets.yaml` (gitignored) — Credentials
- `testing.md` — Test-Prozedur
- `~/homeassistant/_data/.storage/esphome.01KM8CGFCPBJYSX5JT0S2PV1X6` — HA-Integration-Storage
