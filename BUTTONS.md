# CYD Panel - Button Reference

Alle Buttons in `cyd-panel.yaml`. Rot = Backend down (alle Typen).

## Typen

### Push (stateless)
Style: `style_btn` / `style_btn_pressed`. Fuehrt Aktion aus, kein State.
```yaml
- button:
    id: btn_slotX
    styles: style_btn
    pressed: { styles: style_btn_pressed }
    width: 148
    height: 52
    widgets:
      - label: { text: "LABEL", text_font: font_mono_16, align: CENTER }
    on_release:
      - homeassistant.service:
          service: script.turn_on
          data: { entity_id: script.example }
```

### State Switch (stateful)
Wie Push, aber toggelt `input_boolean`. Braucht zusaetzlich einen `text_sensor` Listener:
```yaml
# text_sensor Sektion:
- platform: homeassistant
  id: slotX_state
  entity_id: input_boolean.example
  on_value:
    then:
      - if:
          condition: { lambda: 'return x == "on";' }
          then:
            - lvgl.obj.update: { id: btn_slotX, bg_color: 0x2a1a00, border_color: 0xff8800, clickable: true }
          else:
            - if:
                condition: { lambda: 'return x == "unavailable" || x.empty();' }
                then:
                  - lvgl.obj.update: { id: btn_slotX, bg_color: 0x1a0808, border_color: 0x440000, clickable: false }
                else:
                  - lvgl.obj.update: { id: btn_slotX, bg_color: 0x0d1b2a, border_color: 0x1b4965, clickable: true }
```

### Feed Button (dynamisch, C++)
Erzeugt per Lambda im 30s-Intervall (Zeile ~361-436). Container: `feed_btn_container`.
Fixable: `bg 0x1a0a0a, border 0xe94560`, pressed `0x3a1a1a`, nach fix `border 0x446688`.
Info-only: kein Button, nur Label mit `text 0x00ff88`.
Fix-Dispatch: 1s-Intervall POST nach `http://192.168.1.225:8900/api/feed/fix` (Zeile ~307-324).

### Nav Button
`style_nav` (inaktiv) / `style_nav_active` (aktuelle Seite). 75x24, `on_release: lvgl.page.show`.

## Buttons nach Seite

### CTRL (page_main)
**Grid 4×3 = 12 Slots, einheitlich 72×44** (vorher 3×3 @ 99×44 — Spalten 3→4, Leo 2026-05-21). Container 310×144, FLEX ROW_WRAP, pad 6.

| Slot | ID | Label | Typ | Aktion / Endpoint | State-Entity |
|----|----|-------|-----|--------|--------------|
| 1 | btn_licht | LICHT | Push | POST `/api/licht/helles-licht` | - |
| 2 | btn_slot2 | SYNC | Push | POST `/api/sync_to_vibe` | - |
| 3 | btn_slot3 | BLACKOUT | State | POST `/api/blackout/{on,off}` (amber) | user_blackout (poll) |
| 4 | btn_slot4 | FIRE TV | Push | `script.cortex_firetv` | - |
| 5 | btn_slot5 | THINK | Push | `script.nabu_think` | - |
| 6 | btn_slot6 | PLAY+GAME | State | musik+gaming toggle | - |
| 7 | btn_night | NIGHT | State | POST `/api/night_blackout/toggle` | night_blackout (poll) |
| 8 | btn_lights_only | LICHT-ONLY | State | POST `/api/lights_only/toggle` (gruen) | lights_only (poll) |
| 9 | btn_pdm | PRED-M | State | `input_boolean.toggle` | `input_boolean.cortex_predictive_maintenance` (gruen) |
| 10 | btn_guest | GUEST | State | `input_boolean.toggle` | `input_boolean.guest_mode` (amber) — WD-47, sperrt AWAY |
| 11 | btn_slot11 | — | Platzhalter | (TBD) | - |
| 12 | btn_slot12 | — | Platzhalter | (TBD) | - |

State-Farben: BLACKOUT/GUEST ON=amber(`0x2a1a00/0xff8800`), LICHT-ONLY/PRED-M ON=gruen(`0x00ff44`).
State-Listener (text_sensor): BLACKOUT ~247, GUEST `guest_state` (input_boolean.guest_mode), PRED-M `pdm_state`.

### FEED (page_feed, ~798-904)
Dynamisch — siehe Feed Button oben.

### AUDIO (page_audio, ~909-1228)
Alle Push, alle `homeassistant.action`. Target: `media_player.spotifyplus_leo_nox`.

| Label | Aktion | Zeile |
|-------|--------|-------|
| \|<< | `media_player.media_previous_track` | ~965 |
| PLAY | `media_player.media_play_pause` | ~982 |
| >>\| | `media_player.media_next_track` | ~1001 |
| VOL-/LOW/MID/HIGH/VOL+ | `script.tv_volume_*` | ~1033-1105 |
| ECHO DOT/TOWER/SPEAKER | `script.switch_spotify_to_*` | ~1121-1164 |

### DEV (page_dev, ~1233-1388)
Nur Nav + Slider `slider_threshold` (~1267-1293).

## Styles (Zeile ~471-500)
| ID | bg | border | text |
|----|----|--------|------|
| style_btn | 0x0d1b2a | 0x1b4965 | 0x00ff88 |
| style_btn_pressed | 0x1b4965 | 0x00ff88 | 0x00ffcc |
| style_alert | 0x1a0a0a | 0xe94560 | 0xe94560 |
| style_nav | 0x0f1a3e | 0x00ccff | 0x00ccff |
| style_nav_active | 0x1b4965 | 0x00ff88 | 0x00ffcc |
| style_feed | 0x0a0f1a | 0x1b4965 | 0x00ff88 |
