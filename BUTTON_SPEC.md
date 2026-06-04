# Button-Spec — Schema-Referenz

Single Source of Truth fuer jeden Button auf dem CYD-Panel. Eine YAML-Datei
pro Button unter `specs/buttons/<id>.yaml`. Vom Scaffolder
(`tools/button_scaffolder/scaffold_button.py`) gelesen.

> **Workflow-Kontext:** `NEW_BUTTON_WORKFLOW.md` · **Style-Konventionen:** `BUTTONS.md` · **Anker:** `AGENTS.md` §Button-Scaffolder

## Zwei Button-Typen

| Typ | Hat `state:` Block? | Verhalten |
|---|---|---|
| **stateless** | nein | Sendet POST an Endpoint, fertig. Default-Blau-Style. |
| **stateful** | ja | Pollt GET-Endpoint, faerbt Button — gruen=active, blau=idle, rot=error. |

## Vollstaendiges Schema

```yaml
# ── Pflicht (alle Buttons) ──────────────────────────────────────────
id: <snake_case>           # str, [a-z][a-z0-9_]*. Treibt:
                           #   - btn_<id>            (LVGL widget id)
                           #   - lbl_<id>            (LVGL label id)
                           #   - <id>_active         (global, nur stateful)
                           # Eindeutig im ganzen YAML. Nicht aendern nach
                           # Flash (Cortex-Audit-Logs verlinken auf id).

label: "<TEXT>"            # str, max 8 chars (font_mono_12 auf 99x44 Slot).
                           # Bei stateful: Default, kann via active_label /
                           # idle_label ueberschrieben werden.

page: <CTRL|AUDIO|DEV>     # Welche LVGL-Page. FEED ist dynamisch generiert
                           # und wird vom Scaffolder NICHT unterstuetzt.

slot: <1..9>               # CTRL: Grid-Position (1..9). Pflicht.
                           # AUDIO/DEV: ignored, free-layout via x/y manuell.

endpoint: "/api/<...>"     # str, POST-Endpoint des Cortex. Wird beim Tap
                           # gefeuert. Pflicht. Pfad muss mit /api/ starten.

# ── Optional: state-poll (macht den Button stateful) ────────────────
state:
  endpoint: "/api/<...>"   # GET-Endpoint, liefert JSON.
  poll_interval_s: 5       # int >= 2. Default 5. Niedriger = mehr WLAN-Last.
  response_field: "<key>"  # Leaf-Key im JSON, dessen Value den State bestimmt.
                           # Beispiel: response = {"musik": true, ...}
                           #          → response_field: musik
                           # MVP: nur Top-Level-Leaf. Tiefer geschachtelte
                           # Pfade erfordern Custom-Lambda — siehe Risks.
  active_value: <true|false|"on"|"off"|...>
                           # Wert des response_field, der "gruen/active"
                           # bedeutet. Alles andere = idle (default-blau).
                           # Bool: true/false. String: in Quotes.
  active_label: "<TEXT>"   # optional. Label wenn state=active.
  idle_label:   "<TEXT>"   # optional. Label wenn state=idle.
                           # Wenn beide weggelassen: label bleibt konstant.
```

## Beispiel: stateless

```yaml
id: cortex_apply
label: "APPLY"
page: CTRL
slot: 8
endpoint: /api/apply_current_slot
```

## Beispiel: stateful

```yaml
id: musik
label: "MUSIK"
page: CTRL
slot: 7
endpoint: /api/musik/toggle
state:
  endpoint: /api/musik
  poll_interval_s: 5
  response_field: musik
  active_value: true
  active_label: "PLAYING"
  idle_label: "PAUSED"
```

## Hard-coded Konventionen (NICHT in Spec)

Der Scaffolder fixiert diese Werte — Spec ueberschreibt sie nicht.

| Aspekt | Wert | Rationale |
|---|---|---|
| Active-Style | `bg=0x0d2a14, border=0x00ff88` (gruen) | Mirror blackout-Button |
| Idle-Style | `style_btn` (default-blau) | Konsistent mit restlichen Slots |
| Error-Style | `bg=0x1a0808, border=0xff0000`, `clickable=false` | "Backend down" universal |
| Cortex-Host | `http://192.168.1.225:8900` | Aus cyd-panel.yaml geerbt |
| Widget-Size | `99x44` (CTRL-Grid) | 3x3-Grid-Slot |
| Font | `font_mono_12` | CTRL-Default |
| HTTP-Method action | `POST`, body `{}` | Convention: Cortex-Toggle-Endpoints sind POST |
| HTTP-Method state | `GET`, max_response 256B | Convention |

## Validierung (vom Scaffolder erzwungen)

Spec wird vor Generierung gegen folgende Regeln gepruefen:

- `id` matcht `^[a-z][a-z0-9_]*$` und endet **nicht** auf `_active` (collision mit Global)
- `id` und alle abgeleiteten LVGL-IDs (`btn_<id>`, `lbl_<id>`) existieren noch nicht in `cyd-panel.yaml`
- `page` ist genau einer von `CTRL|AUDIO|DEV`
- `slot` ist 1..9 wenn `page=CTRL`, sonst irrelevant
- bei `page=CTRL`: `id: btn_slot<slot>` muss aktuell ein `—`-Placeholder sein (sonst abort)
- `endpoint` startet mit `/api/`
- `endpoint` ist nicht schon in `~/cortex/main.py` registriert (sonst abort — kein `--force` im MVP)
- bei `state:` vorhanden: `state.endpoint` startet mit `/api/`, `response_field` ist ein einfacher Wort-Key, `poll_interval_s >= 2`
- `active_value` ist `bool` oder `str`

## Risiken / MVP-Grenzen

- **Substring-JSON-Parser:** Block-2-Lambda nutzt `body.find("\"<key>\":<val>")` statt echtem JSON-Parser. Funktioniert nur fuer eindeutige Top-Level-Leaf-Keys. Wenn zwei verschiedene JSON-Pfade denselben Key tragen → false positives. Mitigation: Spec validiert dass `response_field` ein einfacher Wort-Key ist; Cortex-Endpoints fuer stateful-Buttons sollten flache JSON-Antworten liefern.
- **Multi-State** (mehr als active/idle/error): nicht im MVP. Workaround: zwei Buttons mit unterschiedlichen `active_value`.
- **FEED-Page**: dynamisch. Scaffolder lehnt `page=FEED` ab.
- **AUDIO/DEV free-layout**: Scaffolder gibt `x/y` als `# MANUELL` Marker aus, Leo trifft die Position selbst.
- **Cortex-Handler-Body**: nicht auto-generierbar (jeder Handler ist bespoke — Event-Emit, Dispatch, Side-Effects). Block 4 = Stub mit `# TODO` + Kommentar-Patterns. Leo schreibt die Logik.

## Lifecycle einer Spec

1. Leo legt `specs/buttons/<id>.yaml` an
2. `python -m tools.button_scaffolder.scaffold_button specs/buttons/<id>.yaml`
3. Vier Bloecke an stdout → Leo paste-t in `cyd-panel.yaml` + `~/cortex/main.py`
4. Cortex-Handler-Stub wird ausgefleischt (manueller Schritt — Event-Emit etc.)
5. Compile + OTA: `esphome compile cyd-panel.yaml && esphome upload cyd-panel.yaml --device 192.168.1.240`
6. Verify: `curl localhost:8900<state.endpoint>` + Tap-Test am Geraet
7. Spec bleibt im Repo committed → Drift-Lint kann spaeter live-yaml gegen `specs/buttons/*.yaml` verifizieren
