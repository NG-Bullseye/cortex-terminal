# cortex-terminal (CYD-Fleet, ESPHome) — Hinweis fuer LLMs / Cloud-Instanzen

ESP32-basierte CYD-Displays (240×320 TFT + Touch) als Hardware-Frontend fuer Cortex/HA.

## Multidisplay-Architektur (EIN DISPLAY = EIN DEVICE-FILE)
Gemeinsame Plattform liegt in `common/`, jedes Display ist eine duenne Device-YAML im Repo-Root:

- `common/hardware.yaml` — Chip, WiFi (`${static_ip}`), API/OTA, SPI/Display/Touch-Pinout, Outputs, Backlight, Status-LED, Sensoren, Touch-Coord-Globals. Wiederverwendbar, kein UI-ID-Bezug.
- `common/ui_base.yaml` — Fonts + LVGL-Basis (Display/Touch-Bindung, Buffer) + Style-Definitionen. Pages kommen pro Device.
- `cortex-terminal.yaml` — Haupt-Panel (Hostname `cyd-panel`, IP `.240`). Identitaet + voller UI (CTRL/CTRL2/FEED/AUDIO/DEV) + Globals/Intervals/text_sensors.
- `cortex-vvo.yaml` — Zweitdisplay (Hostname `cortex-vvo`, IP `.241`). Spiegelt CTRL2; VVO-Inhalt folgt Welle 3.
- `displays.yaml` — zentrale NAME→IP-Registry (ops-Wahrheit; Device-`substitutions` muessen matchen).

**Neues Display:** Eintrag in `displays.yaml` (freie IP gegen `~/cortex/docs/network-devices.md` pruefen) + `<name>.yaml` mit `substitutions:` (device_name/static_ip) + `packages:` (common) + eigenen `lvgl.pages`. Mehr in README § „Display hinzufuegen".

**Identitaet:** Firmware-`name` (= Hostname, HA-gepairt) wird beim Initial-Flash fix vergeben und NICHT umbenannt — `cyd-panel` bleibt `cyd-panel`, der logische Display-Name ist `cortex-terminal`.

## Vollstaendige Doku → `README.md`

`README.md` enthaelt:
- Hardware (CYD-Pinout, Display + Touch SPI-Buses)
- Deploy-Pipeline (`esphome run cortex-terminal.yaml --device 192.168.1.240`)
- Secrets-Management + api_key-Drift-Pitfall
- Diagnose-Tree
- Pitfalls (WiFi-Env-Vars, Boot-Watchdog, HTTP-Timeout, Touch-Debounce)

`testing.md` enthaelt Test-Verfahren + Acceptance-Criteria.
`BUTTONS.md` und `NEW_BUTTON_WORKFLOW.md` dokumentieren Touch-Layout-Aenderungen.

## Schnelle Orientierung fuer Agent

```bash
cd ~/esp_repos/cortex-terminal
export ESPHOME_WIFI_SSID="..." ESPHOME_WIFI_PASSWORD="..."
esphome run cortex-terminal.yaml --device 192.168.1.240   # OTA + Live-Log
esphome run cortex-terminal.yaml --device /dev/ttyUSB0    # USB-Recovery
```

**Vor jeder Aenderung:** README + testing.md lesen. WiFi-Credentials via Env-Vars exportieren (sonst Build-Fail). CYD-Pinout im YAML nicht ohne Hardware-Doku aendern.
