# cortex-terminal — Agent Brief

## Was ist das
ESP32 + CYD-Display (Cheap Yellow Display, 240×320 Touch) als Hardware-Frontend fuer Cortex. „Nabu Terminal" am PC-Tisch. Touch-Buttons triggern HA-Scripts und Cortex-HTTP-Endpoints, Display zeigt Status/Feed.

```
[CYD Touch] ─on_release─▶ [HA-Service / HTTP] ─▶ Cortex / HA / chat-service
```

## Hardware
- **Chip:** ESP32 (`esp32dev`, ESPHome + LVGL)
- **Hostname:** `cyd-panel`
- **IP:** `192.168.1.240` (statisch)
- **Display:** ILI9341 240×320, Touch XPT2046

## Services (was das Geraet exponiert + nutzt)

| Richtung | Endpoint / Service | Zweck |
|---|---|---|
| ▶ outbound | HA `homeassistant.service` | LICHT, BLACKOUT-Toggle, REBOUND, THINK |
| ▶ outbound | HTTP POST `cortex:8900/api/sync_to_vibe` | SYNC-Button → Cortex Reconciliation |
| ▶ outbound | HTTP POST `cortex:8900/api/licht/helles-licht` (via HA-Script) | LICHT-Button |
| ▶ outbound | HA `script.cortex_firetv` | FIRE-TV-Button (HA → `cortex-claude-chat:8765/firetv`) |
| ◀ inbound | HTTP GET `cyd-panel.local/api/blackout` (vom CYD selbst) | Status-LED-Update |
| ◀ inbound | ESPHome native API zu HA | text_sensor sync (Blackout, Slot-Names) |

## Pages (LVGL — Stand Live-Firmware 2026-04-27)
- **CTRL** — Slot1 LICHT / Slot2 SYNC / Slot3 BLACKOUT / Slot4 FIRE TV / Slot5 THINK
- **FEED** — Watchdog + Nabu-Comms
- **AUDIO** — Beamer-Volume-Buttons (`script.tv_volume_*`)
- **DEV** — Touch-Calibration · `btn_gaming` (Repo, nicht geflashed bis Leo will)
- Nav-Bar unten: CTRL / FEED / AUDIO / DEV
- Header oben: links = Uhrzeit · rechts = IP + aktuelle Zone

## Build / Flash
ESPHome — `esphome run cyd-panel.yaml`. Workflow: `NEW_BUTTON_WORKFLOW.md`.

## Doku-Reihenfolge fuer Agenten
1. `AGENTS.md` (du bist hier)
2. `CLAUDE.md` — Projekt-Memory + LLM-Pointer
3. `README.md` — Hardware-Pinout, ausfuehrliche Architektur
4. `BUTTONS.md` — Button-Type-Reference
5. `testing.md` — Test-Verfahren

## Ground Truth
**Leo.** Real-Beobachtung schlaegt Code-Stand. cyd-panel.yaml im Repo kann hinter dem Live-Geraet zurueck sein.

## Selbstbild — kanonisch in `~/cortex/CLAUDE.md`
Mein Wesen (Identitaet, Kommunikation, Task-System mit Markern ❌/❗/👁, Live-Lage) wird **dort** gewartet — diese Datei nur fuer dieses Repo. Beim Wechsel: `~/cortex/CLAUDE.md` zuerst, dann hier.

Kein Symlink (Repo-Klone-fest), sondern expliziter Pointer.
