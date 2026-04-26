# Workflow: Neuer Button im CYD Panel → HA Script

Schritt-fuer-Schritt Anleitung, um einen neuen Push-Button im `cortex-terminal`
(ESPHome auf CYD) an ein Home Assistant Script zu haengen. Vorbild: `FIRE TV`
Button in `cyd-panel.yaml` (~Zeile 678-693) → `script.cortex_firetv` in HA.

Repo: `~/esp_repos/cortex-terminal/`
Hardware: CYD Panel (ESPHome, LVGL)
Ziel HA: `~/homeassistant/_data/`

## Architektur

```
[CYD Button] --on_release--> [homeassistant.service] --> [HA Script]
                                                            |
                                                 (optional) v
                                                     [rest_command] --> [Backend-Endpoint]
                                                            |
                                                            v
                                                     [Geraete/Cortex/etc.]
```

Der Button ruft immer ein **HA Script** auf — nie direkt ein `rest_command`
oder eine Geraete-Action. Das Script ist die Abstraktionsschicht: wenn sich
das Backend aendert, bleibt der Button stabil.

## Schritte

### 1. Button in `cyd-panel.yaml` anlegen

Auf der richtigen Seite (meist `page_main` / CTRL) einen Slot ergaenzen.
Struktur analog zu FIRE TV (Zeile ~677-693):

```yaml
- button:
    id: btn_slotN                   # fortlaufende ID, eindeutig
    styles: style_btn
    pressed:
      styles: style_btn_pressed
    width: 96                       # an Grid-Layout der Seite anpassen
    height: 52
    widgets:
      - label:
          text: "MEIN BTN"          # Label, max ~8 Zeichen bei font_mono_12
          text_font: font_mono_12
          align: CENTER
    on_release:
      - logger.log: "SLOTN: mein_button"
      - homeassistant.service:
          service: script.mein_button
```

Referenz fuer Styles, Typen und Layout: `BUTTONS.md`.

### 2. HA Script in `scripts.yaml` definieren

Script als schlanker Wrapper. Bei externen Backends via `rest_command`
kapseln (siehe FIRE TV):

```yaml
mein_button:
  alias: Cortex - Mein Button
  sequence:
    - action: rest_command.mein_button      # oder: service: light.turn_on, script.xy, etc.
  mode: single
  icon: mdi:gesture-tap-button
```

Variante ohne externen Endpoint (z.B. direkt Geraet schalten):

```yaml
mein_button:
  alias: Cortex - Mein Button
  sequence:
    - action: light.turn_on
      target: { entity_id: light.wohnzimmer }
  mode: single
```

### 3. (Optional) `rest_command` in `configuration.yaml`

Nur noetig, wenn ein Backend-Endpoint angesprochen wird (Cortex,
eigener HTTP-Service). Beispiel analog FIRE TV (Zeile ~78-81):

```yaml
rest_command:
  mein_button:
    url: "http://172.20.0.10:8900/api/mein/endpoint"   # Cortex-Container IP
    method: POST
    timeout: 10
```

Wichtig:
- Cortex-Container: `172.20.0.10:8900`
- HA-Container: `172.20.0.3:8123`
- Host/LAN: `192.168.1.225`

### 4. Deploy

```bash
# HA: Config neu laden (Scripts + rest_command)
# UI: Entwicklerwerkzeuge → YAML → "Skripte neu laden"
# oder MCP: ha__reload_yaml / HA neu starten

# ESP: CYD Panel flashen
cd ~/esp_repos/cortex-terminal
esphome run cyd-panel.yaml
```

### 5. Test

1. HA UI: Script manuell ausfuehren → Zielwirkung pruefen
2. CYD: Button druecken → Logserial zeigt `SLOTN: mein_button`
3. HA Logs: Script-Trace pruefen (`Entwicklerwerkzeuge → Skripte → Trace`)

## Checkliste

- [ ] Neuer Slot in `cyd-panel.yaml` (eindeutige `id`, passende `width/height`)
- [ ] `on_release` ruft `homeassistant.service: script.<name>`
- [ ] Script in `scripts.yaml` (mit `alias`, `mode: single`, `icon`)
- [ ] Falls externes Backend: `rest_command` in `configuration.yaml`
- [ ] `BUTTONS.md` aktualisiert (Eintrag in Buttons-Tabelle)
- [ ] CYD geflasht + HA Config neu geladen
- [ ] Manueller End-to-End-Test

## Referenzen

- Button-Typen & Styles: `BUTTONS.md`
- FIRE TV Button: `cyd-panel.yaml` ~Zeile 677-693
- `script.cortex_firetv`: `~/homeassistant/_data/scripts.yaml` ~Zeile 450
- `rest_command.cortex_firetv`: `~/homeassistant/_data/configuration.yaml` ~Zeile 78
