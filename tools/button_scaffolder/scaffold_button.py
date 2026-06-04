"""Scaffold a new CYD-Panel button from a YAML spec.

Reads `specs/buttons/<id>.yaml`, validates against schema (BUTTON_SPEC.md),
checks collisions vs cortex-terminal.yaml + ~/cortex/main.py, and prints up to
four framed code-blocks to stdout. NO file writes — pure paste-driven.

Usage:
    python -m tools.button_scaffolder.scaffold_button specs/buttons/<id>.yaml

Exit codes:
    0 = success, blocks printed
    1 = validation error
    2 = collision detected (id / slot / endpoint already used)
    3 = unsupported case (page=FEED, deep response_field, etc.)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from string import Template
from typing import Any

import yaml


# ── Paths (resolved relative to repo root) ─────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
CYD_YAML = REPO_ROOT / "cortex-terminal.yaml"
CORTEX_MAIN = Path.home() / "cortex" / "main.py"

CORTEX_HOST = "http://192.168.1.225:8900"
VALID_PAGES = {"CTRL", "AUDIO", "DEV"}


# ── ANSI for framed output (TTY only, plain ASCII otherwise) ──────────────
def _framed(title: str, body: str) -> str:
    bar = "═" * 79
    return f"{bar}\n{title}\n{bar}\n{body.rstrip()}\n"


def _err(msg: str) -> None:
    print(f"\033[31m✗ {msg}\033[0m", file=sys.stderr)


def _info(msg: str) -> None:
    print(f"\033[36m• {msg}\033[0m", file=sys.stderr)


def _ok(msg: str) -> None:
    print(f"\033[32m✓ {msg}\033[0m", file=sys.stderr)


# ── Spec validation ───────────────────────────────────────────────────────
ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def validate_spec(spec: dict[str, Any], spec_path: Path) -> None:
    required = {"id", "label", "page", "endpoint"}
    missing = required - spec.keys()
    if missing:
        raise ValueError(f"missing required fields: {sorted(missing)}")

    bid = spec["id"]
    if not isinstance(bid, str) or not ID_RE.match(bid):
        raise ValueError(f"id '{bid}' must match {ID_RE.pattern}")
    if bid.endswith("_active"):
        raise ValueError("id must not end with '_active' (collides with global)")

    label = spec["label"]
    if not isinstance(label, str) or not label:
        raise ValueError("label must be non-empty string")

    page = spec["page"]
    if page not in VALID_PAGES:
        if page == "FEED":
            raise SystemExit(
                _err_and_exit(3, "page=FEED not supported (FEED is dynamically generated)")
            )
        raise ValueError(f"page '{page}' must be one of {sorted(VALID_PAGES)}")

    if page == "CTRL":
        slot = spec.get("slot")
        if not isinstance(slot, int) or slot < 1 or slot > 9:
            raise ValueError("slot must be int 1..9 for page=CTRL")

    endpoint = spec["endpoint"]
    if not isinstance(endpoint, str) or not endpoint.startswith("/api/"):
        raise ValueError(f"endpoint '{endpoint}' must start with /api/")

    state = spec.get("state")
    if state is not None:
        if not isinstance(state, dict):
            raise ValueError("state must be a mapping")
        s_ep = state.get("endpoint")
        if not isinstance(s_ep, str) or not s_ep.startswith("/api/"):
            raise ValueError(f"state.endpoint '{s_ep}' must start with /api/")
        s_field = state.get("response_field")
        if not isinstance(s_field, str) or not re.match(r"^[a-z_][a-z0-9_]*$", s_field):
            raise ValueError("state.response_field must be a simple word-key (no dots in MVP)")
        s_poll = state.get("poll_interval_s", 5)
        if not isinstance(s_poll, int) or s_poll < 2:
            raise ValueError("state.poll_interval_s must be int >= 2")
        if "active_value" not in state:
            raise ValueError("state.active_value is required")
        av = state["active_value"]
        if not isinstance(av, (bool, str, int)):
            raise ValueError("state.active_value must be bool / str / int")


def _err_and_exit(code: int, msg: str) -> int:
    _err(msg)
    sys.exit(code)


# ── Collision checks (read-only) ──────────────────────────────────────────
def check_cyd_collisions(spec: dict[str, Any], cyd_text: str, migrate: bool = False) -> str:
    """Returns the slot7-style placeholder block to be REPLACED, or '' if not CTRL.

    With migrate=True, also accepts existing wired buttons (Block 3 will replace them).
    """
    bid = spec["id"]
    btn_id = f"btn_{bid}"
    lbl_id = f"lbl_{bid}"
    global_id = f"{bid}_active"

    if re.search(rf"\bid:\s*{re.escape(btn_id)}\b", cyd_text):
        sys.exit(_err_and_exit(2, f"id collision: 'btn_{bid}' already exists in cortex-terminal.yaml"))
    if re.search(rf"\bid:\s*{re.escape(lbl_id)}\b", cyd_text):
        sys.exit(_err_and_exit(2, f"id collision: 'lbl_{bid}' already exists in cortex-terminal.yaml"))
    if re.search(rf"\bid:\s*{re.escape(global_id)}\b", cyd_text):
        sys.exit(_err_and_exit(2, f"global collision: '{global_id}' already exists"))

    if spec["page"] != "CTRL":
        return ""

    slot = spec["slot"]
    slot_id = f"btn_slot{slot}"
    # Find the slot's existing block
    pat = re.compile(
        rf"(- button:\s*\n(?:\s+#[^\n]*\n)*\s+id:\s*{re.escape(slot_id)}\b.*?)(?=\n              -|\n            \w|\Z)",
        re.DOTALL,
    )
    m = pat.search(cyd_text)
    if not m:
        sys.exit(_err_and_exit(2, f"slot {slot} not found — id '{slot_id}' missing in cortex-terminal.yaml"))

    block = m.group(1)
    # Heuristic: is it still a placeholder? Placeholder has label "—" and no on_release.
    is_placeholder = ('text: "—"' in block) and ("on_release" not in block)
    if not is_placeholder and not migrate:
        sys.exit(_err_and_exit(
            2,
            f"slot {slot} (id={slot_id}) is not a placeholder — already wired. "
            f"Use --migrate to replace an existing button."
        ))
    return block


def check_cortex_collisions(endpoints: list[str]) -> dict[str, bool]:
    """Returns dict[endpoint_path, exists_in_main_py]."""
    if not CORTEX_MAIN.exists():
        _info(f"~/cortex/main.py not found at {CORTEX_MAIN} — skipping collision check")
        return {ep: False for ep in endpoints}
    text = CORTEX_MAIN.read_text()
    result = {}
    for ep in endpoints:
        # Simple literal-string match — covers add_api_route("X", ...) and @app.post("X")
        result[ep] = f'"{ep}"' in text or f"'{ep}'" in text
    return result


# ── Template rendering ────────────────────────────────────────────────────
def load_template(name: str) -> Template:
    path = TEMPLATES_DIR / name
    return Template(path.read_text())


def render_active_value_literal(value: Any) -> str:
    """How to write the active-value into the substring-match string.

    `body.find("\\"<key>\\":<value-literal>")` — matches what JSON serialization
    outputs.
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return f'\\"{value}\\"'
    raise ValueError(f"unsupported active_value type: {type(value)}")


def build_context(spec: dict[str, Any]) -> dict[str, str]:
    bid = spec["id"]
    label = spec["label"]
    endpoint = spec["endpoint"]
    state = spec.get("state") or {}

    ctx = {
        "id": bid,
        "ID": bid.upper(),
        "btn_id": f"btn_{bid}",
        "lbl_id": f"lbl_{bid}",
        "global_id": f"{bid}_active",
        "label_default": label,
        "endpoint": endpoint,
        "action_url": f"{CORTEX_HOST}{endpoint}",
        "slot": str(spec.get("slot", "")),
        "handler_action": f"api_{bid}_action",
        "handler_state": f"api_{bid}_state",
    }

    if state:
        s_ep = state["endpoint"]
        ctx.update({
            "state_endpoint": s_ep,
            "state_url": f"{CORTEX_HOST}{s_ep}",
            "poll_interval_s": str(state.get("poll_interval_s", 5)),
            "response_field": state["response_field"],
            "active_label": state.get("active_label", label),
            "idle_label": state.get("idle_label", label),
            "match_substring": (
                f'\\"{state["response_field"]}\\":{render_active_value_literal(state["active_value"])}'
            ),
        })
    return ctx


# ── Main ──────────────────────────────────────────────────────────────────
def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if not a.startswith("--")]
    flags = {a for a in argv[1:] if a.startswith("--")}
    migrate = "--migrate" in flags

    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        print("\nFlags:\n  --migrate    replace an existing wired button on the same slot", file=sys.stderr)
        return 1

    spec_path = Path(args[0])
    if not spec_path.exists():
        return _err_and_exit(1, f"spec file not found: {spec_path}")

    spec = yaml.safe_load(spec_path.read_text())
    if not isinstance(spec, dict):
        return _err_and_exit(1, "spec must be a YAML mapping")

    try:
        validate_spec(spec, spec_path)
    except ValueError as e:
        return _err_and_exit(1, f"spec validation: {e}")

    _ok(f"spec '{spec['id']}' valid")

    is_stateful = spec.get("state") is not None
    btype = "stateful" if is_stateful else "stateless"
    _info(f"type: {btype} · page: {spec['page']} · slot: {spec.get('slot', '—')}")

    # Collision checks
    cyd_text = CYD_YAML.read_text()
    placeholder = check_cyd_collisions(spec, cyd_text, migrate=migrate)
    if migrate:
        _ok(f"cortex-terminal.yaml: id '{spec['id']}' free, slot will be MIGRATED (existing button replaced)")
    else:
        _ok(f"cortex-terminal.yaml: id '{spec['id']}' free, slot ready")

    endpoints_to_check = [spec["endpoint"]]
    if is_stateful:
        endpoints_to_check.append(spec["state"]["endpoint"])
    cortex_existing = check_cortex_collisions(endpoints_to_check)

    new_endpoints = [ep for ep, exists in cortex_existing.items() if not exists]
    existing_endpoints = [ep for ep, exists in cortex_existing.items() if exists]
    for ep in existing_endpoints:
        _info(f"cortex: endpoint {ep} already exists — Block 4 will skip it")
    for ep in new_endpoints:
        _info(f"cortex: endpoint {ep} is NEW — Block 4 will emit stub")

    # Build context + render
    ctx = build_context(spec)

    # ── Block 1: globals (only stateful) ──
    print()
    if is_stateful:
        block1 = load_template("globals.txt").substitute(ctx)
        print(_framed(
            "BLOCK 1 of 4 — paste into cortex-terminal.yaml `globals:` section\n"
            "INSERTION: search for comment '# Cortex User-Blackout state' (~line 192).\n"
            "           Append below the existing `- id: blackout_active` block.",
            block1,
        ))
    else:
        print(_framed(
            "BLOCK 1 — SKIP (stateless button needs no global)",
            "(no output)",
        ))

    # ── Block 2: interval poll (only stateful) ──
    if is_stateful:
        block2 = load_template("interval_poll.txt").substitute(ctx)
        print(_framed(
            "BLOCK 2 of 4 — paste into cortex-terminal.yaml `interval:` section\n"
            "INSERTION: search for comment '# Poll Cortex User-Blackout state' (~line 303).\n"
            "           Append AFTER that block as a new sibling under `interval:`.",
            block2,
        ))
    else:
        print(_framed(
            "BLOCK 2 — SKIP (stateless button needs no polling)",
            "(no output)",
        ))

    # ── Block 3: widget ──
    tmpl_name = "widget_stateful.txt" if is_stateful else "widget_stateless.txt"
    block3 = load_template(tmpl_name).substitute(ctx)
    if spec["page"] == "CTRL":
        slot = spec["slot"]
        insertion = (
            f"INSERTION: in cortex-terminal.yaml, search 'id: btn_slot{slot}' on page_main.\n"
            f"           REPLACE the entire `- button:` placeholder block with this widget."
        )
    else:
        insertion = (
            f"INSERTION: in cortex-terminal.yaml on page_{spec['page'].lower()}.\n"
            f"           Insert as a new `- button:` widget. NOTE: free-layout page —\n"
            f"           you must add `x:` and `y:` manually (see existing widgets on page)."
        )
    print(_framed(
        f"BLOCK 3 of 4 — widget for {btype} '{spec['id']}'\n{insertion}",
        block3,
    ))

    # ── Block 4: cortex routes (only when new endpoints) ──
    if new_endpoints:
        # Build state-handler-block + state-route-line dynamically based on what's new
        state_handler_block = ""
        state_route_line = ""
        if is_stateful and not cortex_existing[spec["state"]["endpoint"]]:
            state_handler_block = (
                f"async def {ctx['handler_state']}():\n"
                f"    log.info(\"HTTP {spec['state']['endpoint']}: {ctx['ID']} state -- TODO implement\")\n"
                f"    # SCAFFOLDER STUB. Return JSON with leaf-key '{ctx['response_field']}'\n"
                f"    # such that the substring 'response_field: active_value' matches when active.\n"
                f"    # Example: {{\"{ctx['response_field']}\": True}}\n"
                f"    return {{\"{ctx['response_field']}\": False}}\n\n"
            )
            state_route_line = (
                f'api.add_api_route("{spec["state"]["endpoint"]}", '
                f'{ctx["handler_state"]}, methods=["GET"])'
            )
        if cortex_existing.get(spec["endpoint"], False):
            # action endpoint already exists -> skip handler stub for it
            block4 = (
                f"# Action endpoint {spec['endpoint']} already exists in main.py — skip.\n"
                f"# Only state-handler is new:\n\n"
                f"{state_handler_block}"
                f"{state_route_line}\n"
            )
        else:
            block4 = load_template("cortex_routes.txt").substitute({
                **ctx,
                "state_handler_block": state_handler_block,
                "state_route_line": state_route_line,
            })
        print(_framed(
            "BLOCK 4 of 4 — paste into ~/cortex/main.py\n"
            "INSERTION: handlers near the existing handler defs (~line 280-340),\n"
            "           routes after the last `api.add_api_route(...)` (~line 480-495).\n"
            "REMEMBER: `cd ~/cortex && docker compose build cortex && docker compose up -d cortex`",
            block4,
        ))
    else:
        print(_framed(
            "BLOCK 4 — SKIP (all endpoints already exist in cortex/main.py)",
            "(no output — no Cortex changes needed)",
        ))

    # ── Closing checklist ──
    blocks_needed = []
    if is_stateful:
        blocks_needed.extend(["1 (global)", "2 (poll)"])
    blocks_needed.append("3 (widget)")
    if new_endpoints:
        blocks_needed.append("4 (cortex)")
    _ok(f"done. Blocks to paste: {', '.join(blocks_needed)}")
    print(file=sys.stderr)
    print(
        "Next steps:\n"
        f"  1. Paste blocks above into cortex-terminal.yaml + ~/cortex/main.py\n"
        f"  2. (if Block 4) Cortex: ausfleischen + rebuild + restart\n"
        f"  3. CYD: esphome compile cortex-terminal.yaml && esphome upload cortex-terminal.yaml --device 192.168.1.240\n"
        f"  4. Test: curl + Tap am Geraet (siehe NEW_BUTTON_WORKFLOW.md §7)\n",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
