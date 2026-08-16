#!/usr/bin/env python3
"""build_cards.py — Modell + Backend → Lovelace-YAML (cards/local/*.yaml).

Aus einem validierten Modell (data/local/*.model.json) wird eine HA-Lovelace-View
generiert mit:
  - Szenarien-Buttons (Harmony-Activity starten/stoppen)
  - Geräte-Fernbedienungen als grid-Karten mit allen Commands

P2-Einschränkung: Geräte-Cards statisch (immer sichtbar).
Conditional-Einblendung per aktivem Szenario kommt in P3.

Aufruf:
  python3 generator/build_cards.py \\
    --model data/local/wz.model.json --out cards/local/wz.yaml
"""
import argparse, json, os, sys
try:
    import yaml
except ImportError:
    print("FEHLER: PyYAML fehlt — pip install pyyaml", file=sys.stderr)
    sys.exit(1)

# Bekannte Command-IDs → (Anzeige-Label, MDI-Icon)
COMMAND_META = {
    "PowerOn":        ("Power On",   "mdi:power-on"),
    "PowerOff":       ("Power Off",  "mdi:power-off"),
    "PowerToggle":    ("Power",      "mdi:power"),
    "VolumeUp":       ("Vol +",      "mdi:volume-plus"),
    "VolumeDown":     ("Vol -",      "mdi:volume-minus"),
    "Mute":           ("Mute",       "mdi:volume-mute"),
    "ChannelUp":      ("CH +",       "mdi:chevron-up"),
    "ChannelDown":    ("CH -",       "mdi:chevron-down"),
    "ChannelPrev":    ("CH Prev",    "mdi:swap-horizontal"),
    "DirectionUp":    ("▲",          "mdi:arrow-up"),
    "DirectionDown":  ("▼",          "mdi:arrow-down"),
    "DirectionLeft":  ("◀",          "mdi:arrow-left"),
    "DirectionRight": ("▶",          "mdi:arrow-right"),
    "OK":             ("OK",         "mdi:checkbox-marked-circle"),
    "Select":         ("OK",         "mdi:checkbox-marked-circle"),
    "Back":           ("Back",       "mdi:arrow-left-circle"),
    "Exit":           ("Exit",       "mdi:close-circle"),
    "Menu":           ("Menu",       "mdi:menu"),
    "Home":           ("Home",       "mdi:home"),
    "Guide":          ("Guide",      "mdi:television-guide"),
    "Info":           ("Info",       "mdi:information"),
    "Play":           ("Play",       "mdi:play"),
    "Pause":          ("Pause",      "mdi:pause"),
    "Stop":           ("Stop",       "mdi:stop"),
    "Rewind":         ("◀◀",         "mdi:rewind"),
    "FastForward":    ("▶▶",         "mdi:fast-forward"),
    "SkipBack":       ("|◀",         "mdi:skip-previous"),
    "SkipForward":    ("▶|",         "mdi:skip-next"),
    "Record":         ("Rec",        "mdi:record-rec"),
    "Netflix":        ("Netflix",    "mdi:netflix"),
    "Apps":           ("Apps",       "mdi:apps"),
    "Settings":       ("Einst.",     "mdi:cog"),
    "Sleep":          ("Sleep",      "mdi:sleep"),
    "Delete":         ("Delete",     "mdi:delete"),
    "Subtitle":       ("Sub",        "mdi:subtitles"),
    "Teletext":       ("TXT",        "mdi:text"),
    "Ambilight":      ("Ambi",       "mdi:lightbulb"),
    "SmartMenu":      ("Smart",      "mdi:star"),
    "Green":          ("Grün",       "mdi:square"),
    "Red":            ("Rot",        "mdi:square"),
    "Yellow":         ("Gelb",       "mdi:square"),
    "Blue":           ("Blau",       "mdi:square"),
    "List":           ("Liste",      "mdi:format-list-bulleted"),
    "Options":        ("Options",    "mdi:dots-horizontal"),
    "InputHdmi1":     ("HDMI 1",     "mdi:hdmi-port"),
    "InputHdmi2":     ("HDMI 2",     "mdi:hdmi-port"),
    "InputHdmi3":     ("HDMI 3",     "mdi:hdmi-port"),
    "InputHdmi4":     ("HDMI 4",     "mdi:hdmi-port"),
    "InputYPbPr":     ("YPbPr",      "mdi:video-input-component"),
    "2D":             ("2D",         "mdi:television"),
    "3D":             ("3D",         "mdi:television-play"),
    "0":  ("0","mdi:numeric-0"), "1":("1","mdi:numeric-1"), "2":("2","mdi:numeric-2"),
    "3":  ("3","mdi:numeric-3"), "4":("4","mdi:numeric-4"), "5":("5","mdi:numeric-5"),
    "6":  ("6","mdi:numeric-6"), "7":("7","mdi:numeric-7"), "8":("8","mdi:numeric-8"),
    "9":  ("9","mdi:numeric-9"),
}

SCENARIO_ICONS = {}  # kann per --scenario-icons JSON erweitert werden


def resolve_cmd(cmd):
    cid = cmd["id"]
    meta = COMMAND_META.get(cid, (cmd.get("label", cid), None))
    label = cmd.get("label") or meta[0]
    icon  = cmd.get("icon")  or meta[1]
    return label, icon


def make_action(service, entity_id, data):
    a = {
        "action": "perform-action",
        "perform_action": service,
        "target": {"entity_id": entity_id},
    }
    if data:
        a["data"] = data
    return a


def build_scenario_row(model, hub):
    """horizontal-stack: ein Button je Szenario + Aus."""
    cards = []
    for s in model["scenarios"]:
        if s["hub"] != hub["id"]:
            continue
        activity = (s.get("backend") or {}).get("harmony", {}).get("activity", s["name"])
        icon = SCENARIO_ICONS.get(s["id"], "mdi:play-circle")
        cards.append({
            "type": "button",
            "name": s["name"],
            "icon": icon,
            "tap_action": make_action("remote.turn_on", hub["entity"], {"activity": activity}),
        })
    cards.append({
        "type": "button",
        "name": "Aus",
        "icon": "mdi:power-off",
        "tap_action": make_action("remote.turn_off", hub["entity"], None),
    })
    return {"type": "horizontal-stack", "cards": cards}


def build_device_card(device, hub):
    """grid-Karte (4 Spalten) mit allen Commands eines Geräts."""
    backend_name = hub["backend"]
    dev_binding  = (device.get("backend") or {}).get(backend_name, {}).get("device", device["name"])
    btns = []
    for cmd in device.get("commands", []):
        label, icon = resolve_cmd(cmd)
        btn = {
            "type": "button",
            "name": label,
            "tap_action": make_action(
                "remote.send_command",
                hub["entity"],
                {"device": dev_binding, "command": cmd["id"]},
            ),
        }
        if icon:
            btn["icon"] = icon
        btns.append(btn)
    return {
        "type": "grid",
        "title": device["name"],
        "columns": 4,
        "square": False,
        "cards": btns,
    }


def build_view(model, hub):
    dev_by_id = {d["id"]: d for d in model["devices"]}
    cards = [build_scenario_row(model, hub)]
    # Reihenfolge: wie Geräte im ersten Szenario des Hubs auftauchen (keine Dopplung)
    seen = []
    for s in model["scenarios"]:
        if s["hub"] != hub["id"]:
            continue
        for did in s["devices"]:
            if did not in seen and did in dev_by_id:
                seen.append(did)
    for did in seen:
        cards.append(build_device_card(dev_by_id[did], hub))
    return {
        "title": hub["name"],
        "path": f"fb-{hub['id']}",
        "icon": "mdi:sofa",
        "cards": cards,
    }


def main():
    ap = argparse.ArgumentParser(description="Modell → Lovelace-YAML (P2: statisch)")
    ap.add_argument("--model", required=True, help="data/local/*.model.json")
    ap.add_argument("--out",   required=True, help="Ausgabepfad, z.B. cards/local/wz.yaml")
    a = ap.parse_args()

    model = json.load(open(a.model, encoding="utf-8"))
    views = [build_view(model, h) for h in model["hubs"]]

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write("# Generiert von generator/build_cards.py (scenario-remote-control)\n")
        f.write("# NICHT manuell editieren — Quelle: " + a.model + "\n")
        f.write("# P2: Geraete-Cards statisch (alle sichtbar) — conditional Einblendung kommt P3\n\n")
        yaml.dump({"views": views}, f, allow_unicode=True, sort_keys=False,
                  default_flow_style=False)

    n_cards = sum(len(v["cards"]) for v in views)
    n_btns  = sum(
        sum(len(c.get("cards", [])) for c in v["cards"] if c.get("type") == "grid")
        for v in views
    )
    print(f"OK: {a.out} — {len(views)} View(s), {n_cards} Karte(n), ~{n_btns} Buttons")


if __name__ == "__main__":
    main()
