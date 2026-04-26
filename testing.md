# Testing — cortex-terminal (CYD Panel, ESPHome)

Belastbare Test-Schleife fuer dieses ESP-Geraet. **Software-Tests reichen nicht** — Subagenten haben keine Sinne, die Realitaet wird vom User bestaetigt (Gate G8 im Multi-Agent-Flow).

## Geraete-Fakten

| Wert | Inhalt |
|---|---|
| Hostname | `cyd-panel` |
| IP (statisch) | `192.168.1.240` |
| MAC | `b0:cb:d8:da:b9:ec` |
| Chip | ESP32 (CYD board, 240×320 TFT mit Touch) |
| YAML | `cyd-panel.yaml` (in diesem Repo) |
| api_key location | `secrets.yaml: api_key:` |
| ota_password | `secrets.yaml: ota_password:` |
| HA Integration entry_id | `01KM8CGFCPBJYSX5JT0S2PV1X6` (`/home/leona/homeassistant/_data/.storage/esphome.<entry_id>`) |
| Wichtige HA-Endpoints aus YAML | `http://192.168.1.225:8900/api/blackout`, `…/feed`, `…/sync_to_vibe`, `http://192.168.1.225:8123/api/services/script/turn_on` |

## Warum dieses Setup

1. **`esphome` CLI** lokal: `/home/leona/.local/bin/esphome`. Unabhaengig vom HA-Container.
2. **OTA + Remote-Logs** sind das Ziel — USB nur fuer Erstinstallation/Recovery.
3. **api_key vs ota_password sind unterschiedliche Keys** — nicht verwechseln:
   - `api_key` = Noise-Encryption HA ↔ ESP. Drift → HA-Entity `unavailable`.
   - `ota_password` = OTA-Flash-Auth. Drift → Upload-Fail.

## Standard-Schleife

1. **YAML editieren** in diesem Repo.
2. **OTA-Flash**:
   ```bash
   esphome run cyd-panel.yaml --device 192.168.1.240
   ```
3. **Remote-Logs**:
   ```bash
   esphome logs cyd-panel.yaml --device 192.168.1.240
   ```
4. **End-to-End-Trigger**: je nach Funktion — Touch-Press am Panel ODER HTTP-Endpoint manuell aufrufen, der vom Panel verbraucht wird (siehe `BUTTONS.md`, `NEW_BUTTON_WORKFLOW.md`).
5. **HITL (G8): Leo bestaetigt** dass UI/Touch/HA-Reaktion real wie erwartet ist.

## Erst-Setup / Recovery (USB-Pfad)

```bash
# CYD per USB anschliessen, /dev/ttyUSBN ermitteln:
ls -la /dev/ttyUSB*

esphome run cyd-panel.yaml --device /dev/ttyUSB0
```

## Diagnose: HA-Entity `unavailable`

```bash
# 1. Pingt ESP?
ping -c 2 192.168.1.240

# 2. Faengt ESPHome-API auf 6053?
timeout 2 bash -c 'cat < /dev/tcp/192.168.1.240/6053'  # exit 124 = port offen, hangt auf Protobuf (normal)

# 3. Verbindet `esphome logs` mit current secrets.yaml?
esphome logs cyd-panel.yaml --device 192.168.1.240
#  → "Successful handshake" = ESP hat den Key aus diesem Repo
#  → Auth fail = ESP hat anderen Key

# 4. Welchen Key hat HA gespeichert?
grep -A2 cyd-panel /home/leona/homeassistant/_data/.storage/core.config_entries
#  → `noise_psk` muss == `api_key` aus secrets.yaml sein

# 5. HA-Integration-Reload:
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" \
     http://192.168.1.225:8123/api/config/config_entries/entry/01KM8CGFCPBJYSX5JT0S2PV1X6/reload
```

### Key-Drift-Recovery

- **Pfad A (script):** `secrets.yaml` auf den HA-Wert setzen + ESP via OTA/USB neu flashen.
- **Pfad B (UI):** HA → Settings → Devices → ESPHome `cyd-panel` loeschen + neu hinzufuegen + Key paste.

Pfad A bevorzugt. Vorher `cp secrets.yaml secrets.yaml.bak-<datum>`.

## Acceptance-Criteria fuer Test-Lauf

- [ ] `esphome run --device 192.168.1.240` → "OTA successful"
- [ ] CYD-Panel-Entities in HA `available`
- [ ] Touch / Trigger der zu testenden Funktion fuehrt zum erwarteten ESP-Log-Eintrag
- [ ] Folge-HTTP-Calls ans Cortex/HA gehen raus (in `esphome logs` sichtbar)
- [ ] **Leo HITL**: UI / Display / Reaktion real wie erwartet

## Self-Test reicht NICHT

ESPHome-Logs zeigen nur Code-Side. Sie zeigen NICHT:
- ob der Touchpoint ergonomisch trifft
- ob das Display lesbar ist
- ob die UX zum Vibe passt

Deshalb: Subagent claimt `ready-for-test` — `done` entscheidet Leo.
