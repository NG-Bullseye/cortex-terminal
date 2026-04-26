# cortex-terminal (CYD-Panel, ESPHome) — Hinweis fuer LLMs / Cloud-Instanzen

ESP32-basiertes CYD-Display (240×320 TFT + Touch) am PC-Tisch. Hardware-Frontend fuer Cortex/HA. Hostname `cyd-panel`, IP `192.168.1.240`.

## Vollstaendige Doku → `README.md`

`README.md` enthaelt:
- Hardware (CYD-Pinout, Display + Touch SPI-Buses)
- Deploy-Pipeline (`esphome run cyd-panel.yaml --device 192.168.1.240`)
- Secrets-Management + api_key-Drift-Pitfall
- Diagnose-Tree
- Pitfalls (WiFi-Env-Vars, Boot-Watchdog, HTTP-Timeout, Touch-Debounce)

`testing.md` enthaelt Test-Verfahren + Acceptance-Criteria.
`BUTTONS.md` und `NEW_BUTTON_WORKFLOW.md` dokumentieren Touch-Layout-Aenderungen.

## Schnelle Orientierung fuer Agent

```bash
cd ~/esp_repos/cortex-terminal
export ESPHOME_WIFI_SSID="..." ESPHOME_WIFI_PASSWORD="..."
esphome run cyd-panel.yaml --device 192.168.1.240   # OTA + Live-Log
esphome run cyd-panel.yaml --device /dev/ttyUSB0    # USB-Recovery
```

**Vor jeder Aenderung:** README + testing.md lesen. WiFi-Credentials via Env-Vars exportieren (sonst Build-Fail). CYD-Pinout im YAML nicht ohne Hardware-Doku aendern.
