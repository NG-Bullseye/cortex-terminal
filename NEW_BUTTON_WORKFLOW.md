# Workflow: Neuer Button (Scaffolder-Driven)

Schritt-fuer-Schritt fuer einen neuen Button auf dem CYD-Panel. Spec-driven,
direkt zu Cortex (kein HA-Detour). Vorbild: Slot 3 Blackout-Button
(`cortex-terminal.yaml` ~672-697 + Polling ~302-342 + Global ~192-196).

> **Schema-Referenz:** `BUTTON_SPEC.md` · **Style/Visual:** `BUTTONS.md` · **Anker:** `AGENTS.md`

## Architektur

```
[CYD Tap] --on_release--> [http_request.post]
                              ↓
                    http://192.168.1.225:8900/api/<endpoint>   (Cortex)
                              ↓
                    Event-Emit / Action-Dispatch / Engine-Call
                              ↓
                    Devices / Spotify / HA-Service (Cortex-intern)

[Optional, nur stateful Buttons]
[5s interval] --http_request.get--> /api/<state-endpoint>
                              ↓
                    Lambda: substring-match → bg/border/clickable
```

**Kein HA-Script-Detour mehr.** Wenn ein Button parallel via Voice/Alexa
schaltbar sein soll, separates `script.<name>` in HA → ruft denselben
`/api/<endpoint>` per `rest_command`. Das ist ein **separater** Schritt,
nicht Teil dieses Workflows.

## Voraussetzungen

- Cortex-Container laeuft (`docker ps | grep cortex`)
- CYD ist online (`ping 192.168.1.240`)
- ESPHome installiert
- Python 3.11+ (Scaffolder-Runtime)

## Schritte

### 1. Spec anlegen

`specs/buttons/<id>.yaml` schreiben. Schema: `BUTTON_SPEC.md`. Beispiele:

- `specs/buttons/_example_stateless.yaml` — stateless Push-Button
- `specs/buttons/_example_stateful.yaml` — stateful Toggle-Button mit Polling

Beim Anlegen:
- `id` muss eindeutig sein (Scaffolder validiert)
- `slot` muss aktuell ein `—`-Placeholder sein
- `endpoint` darf nicht schon in `~/cortex/main.py` registriert sein

### 2. Scaffolder ausfuehren

```bash
cd ~/esp_repos/cortex-terminal
python -m tools.button_scaffolder.scaffold_button specs/buttons/<id>.yaml
```

Output: vier framed Bloecke an stdout, mit Insertion-Anweisungen.

| Block | Zielort | Wann | Was |
|---|---|---|---|
| **1** | `cortex-terminal.yaml` `globals:` | nur stateful | `<id>_active` Bool-Global |
| **2** | `cortex-terminal.yaml` `interval:` | nur stateful | 5s GET-Poll + Lambda |
| **3** | `cortex-terminal.yaml` `pages:` | immer | LVGL-Widget + on_release |
| **4** | `~/cortex/main.py` | wenn Endpoint neu | FastAPI-Route-Stub |

Stateless ohne neuen Endpoint = nur Block 3. Stateful mit neuem Endpoint =
alle vier. Scaffolder sagt im Output explizit welche Bloecke noetig sind.

### 3. Bloecke einsetzen

Jeder Block hat einen Anker-Kommentar fuer die Suche. Beispiel-Anker fuer
Block 3 auf CTRL: `# Slot 7-9: Platzhalter` (`cortex-terminal.yaml` ~742). Block 3
ersetzt den `—`-Placeholder-Block.

Block 1 (globals): unter `# Cortex User-Blackout state` (~192) anhaengen.

Block 2 (interval): nach dem `# Poll Cortex User-Blackout state` Block (~342)
als neuen Sibling im `interval:` einsetzen.

Block 4 (FastAPI): in `~/cortex/main.py` unter den existierenden
`api.add_api_route(...)`-Aufrufen anhaengen. Handler-Stub wird ueber den
existierenden Handlern (z.B. neben `blackout_on`) eingefuegt.

### 4. Cortex-Handler-Body schreiben

Block 4 ist ein **Stub** mit `# TODO`. Leo (oder ein Cortex-Subagent)
schreibt die echte Logik. Patterns:

```python
# Pattern A: Event emittieren (haeufig)
from events.<modul> import <EventName>
gateway.emit(<EventName>(...))

# Pattern B: Direkter Store-Dispatch
store.dispatch(CortexAction(action=store_actions.<x>(),
                            keys=USER_KEYS, source="api.<id>"))

# Pattern C: Engine-Methode aufrufen
await engine.<name>.<method>()
```

Antwort-Shape: bei stateful-Buttons MUSS der GET-Endpoint JSON liefern
mit dem `response_field` als Top-Level-Leaf — sonst funktioniert der
Substring-Parser im Lambda nicht. Beispiel: Spec `response_field: musik` →
GET-Antwort enthaelt `{"musik": true, ...}` (egal in welchem Kontext, solange
`"musik":true` als Substring auftaucht).

### 5. Cortex deployen (wenn Block 4 noetig war)

```bash
cd ~/cortex
docker compose build cortex && docker compose up -d cortex
curl -s http://localhost:8900<endpoint> | head    # Smoke-Test
```

### 6. CYD flashen

```bash
cd ~/esp_repos/cortex-terminal
ping -c 2 -W 2 192.168.1.240                              # Reachability
esphome compile cortex-terminal.yaml                            # ~150s
esphome upload  cortex-terminal.yaml --device 192.168.1.240     # ~6s OTA
ping -c 1 192.168.1.240                                   # verify back
```

Details + Gotchas: `AGENTS.md` §"Build / Flash (OTA)".

### 7. Test

1. **Endpoint manuell:** `curl -X POST http://localhost:8900<endpoint>`
   → erwartete Reaktion (Logs in cortex-Container).
2. **State-Endpoint manuell:** `curl http://localhost:8900<state.endpoint>`
   → JSON enthaelt `response_field: <active_value>`.
3. **Button am Geraet:** Tap → `logger.log` in seriellen ESPHome-Logs sichtbar
   (`esphome logs cortex-terminal.yaml --device 192.168.1.240`).
4. **State-Sync:** State im Cortex aendern (z.B. zweiter Endpoint-Call) →
   Button-Farbe folgt innerhalb `poll_interval_s`.
5. **Error-Handling:** `docker stop cortex` → Button wird rot + non-clickable.
   `docker start cortex` → recover.

## Checkliste

- [ ] `specs/buttons/<id>.yaml` angelegt + valide
- [ ] Scaffolder ohne Errors gelaufen
- [ ] Block 1 (Global, falls stateful) eingesetzt
- [ ] Block 2 (Interval-Poll, falls stateful) eingesetzt
- [ ] Block 3 (Widget) eingesetzt — `—`-Placeholder ersetzt
- [ ] Block 4 (FastAPI-Route, falls Endpoint neu) eingesetzt
- [ ] Cortex-Handler-Body ausgefleischt + getestet
- [ ] Cortex rebuild + restart (wenn Block 4 noetig war)
- [ ] CYD compile + OTA erfolgreich
- [ ] Endpoint via curl reagiert
- [ ] Button reagiert auf Tap
- [ ] State-Sync verifiziert (stateful)
- [ ] Error-Recovery verifiziert (stateful)
- [ ] `BUTTONS.md` Tabelle ergaenzt
- [ ] Spec committed

## Migration alter HA-Detour-Buttons

Existierende Buttons (z.B. Slot 5 THINK → `script.nabu_think`) koennen
nachtraeglich auf direct-to-Cortex umgestellt werden:

1. Spec fuer den Button schreiben mit dessen aktueller `id` (z.B. `id: think`)
2. Cortex-Endpoint anlegen, der das HA-Script-Verhalten emuliert
3. Block 3 ersetzt das alte `homeassistant.service:`-Widget
4. HA-Script + `rest_command` koennen optional bleiben fuer Voice-Pfad

## Referenzen

- Schema: `BUTTON_SPEC.md`
- Visuell: `BUTTONS.md`
- Beispiele: `specs/buttons/_example_*.yaml`
- Vorbild-Implementation: Slot 3 Blackout-Button (`cortex-terminal.yaml` ~672-697 + ~302-342 + ~192-196)
- Cortex-Endpoint-Pattern: `~/cortex/main.py` Suche nach `add_api_route`
