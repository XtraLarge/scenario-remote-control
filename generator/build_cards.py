#!/usr/bin/env python3
"""build_cards.py — Modell → Lovelace-YAML (custom:universal-remote-card).

Quellen-abstrakt: das Modell (data/local/*.model.json) ist backend-unabhängig.
Dieser Generator kennt nur das Modell-Format — welche Quelle es erzeugt hat
(Harmony, Broadlink, ESPHome-IR …) ist für die Karten-Generierung irrelevant.

Erzeugt:
  - Sections-View mit Szenarien-Switcher (URC + custom_actions/rows)
  - Geräte-Karten (URC, Smart-Templates: circlepad/dpad, Zahlen, Volume)
  - P3: Conditional-Einblendung via binary_sensor.<hub>_show_card_<device>

Aufruf:
  python3 generator/build_cards.py \\
    --model data/local/wz.model.json --out cards/local/wz.yaml
"""
import argparse, json, os, sys
try:
    import yaml
except ImportError:
    sys.exit("FEHLER: pip install pyyaml")

# ── Icons ─────────────────────────────────────────────────────────────────────
ICONS = {
    "PowerOn":"mdi:power-on","PowerOff":"mdi:power-off","PowerToggle":"mdi:power",
    "VolumeUp":"mdi:volume-plus","VolumeDown":"mdi:volume-minus","Mute":"mdi:volume-mute",
    "ChannelUp":"mdi:chevron-up","ChannelDown":"mdi:chevron-down","ChannelPrev":"mdi:swap-horizontal",
    "DirectionUp":"mdi:arrow-up","DirectionDown":"mdi:arrow-down",
    "DirectionLeft":"mdi:arrow-left","DirectionRight":"mdi:arrow-right",
    "OK":"mdi:circle","Select":"mdi:circle",
    "Back":"mdi:arrow-left-circle","Exit":"mdi:close-circle",
    "Menu":"mdi:menu","Home":"mdi:home-outline",
    "Guide":"mdi:television-guide","Info":"mdi:information-outline",
    "Play":"mdi:play","Pause":"mdi:pause","Stop":"mdi:stop",
    "Rewind":"mdi:rewind","FastForward":"mdi:fast-forward",
    "SkipBack":"mdi:skip-previous","SkipForward":"mdi:skip-next",
    "Record":"mdi:record-rec","Delete":"mdi:delete-outline",
    "Apps":"mdi:apps","Netflix":"mdi:netflix",
    "Settings":"mdi:cog-outline","Sleep":"mdi:sleep",
    "Subtitle":"mdi:subtitles-outline","Teletext":"mdi:text",
    "Ambilight":"mdi:lightbulb-outline","SmartMenu":"mdi:star-outline",
    "List":"mdi:format-list-bulleted","Options":"mdi:dots-horizontal",
    "Green":"mdi:square","Red":"mdi:square","Yellow":"mdi:square","Blue":"mdi:square",
    "InputHdmi1":"mdi:hdmi-port","InputHdmi2":"mdi:hdmi-port",
    "InputHdmi3":"mdi:hdmi-port","InputHdmi4":"mdi:hdmi-port",
    **{str(n): f"mdi:numeric-{n}" for n in range(10)},
}

SCENARIO_ICONS = {
    "sky":"mdi:satellite-uplink","firetv":"mdi:microphone",
    "android":"mdi:television","bluetooth":"mdi:bluetooth",
    "radio":"mdi:radio","ps":"mdi:sony-playstation",
}

# ── Helfer ────────────────────────────────────────────────────────────────────
def ic(cmd_id): return ICONS.get(cmd_id)

def send(hub_entity, dev_id, cmd_id):
    return {"action":"perform-action","perform_action":"remote.send_command",
            "target":{"entity_id":hub_entity},"data":{"device":dev_id,"command":cmd_id}}

def btn(name, cmd_id, hub_entity, dev_id, label=None):
    b = {"type":"button","name":name,"tap_action":send(hub_entity,dev_id,cmd_id),"haptics":True}
    i = ic(cmd_id)
    if i: b["icon"] = i
    if label: b["label"] = label
    return b

def circlepad(hub_entity, dev_id, ok_cmd="OK"):
    def d(cmd): return {"tap_action":send(hub_entity,dev_id,cmd),"hold_action":{"action":"repeat"}}
    return {"type":"circlepad","name":"circlepad",
            "tap_action":send(hub_entity,dev_id,ok_cmd),
            "up":{**d("DirectionUp"),"icon":"mdi:chevron-up"},
            "down":{**d("DirectionDown"),"icon":"mdi:chevron-down"},
            "left":{**d("DirectionLeft"),"icon":"mdi:chevron-left"},
            "right":{**d("DirectionRight"),"icon":"mdi:chevron-right"},
            "haptics":True}

def dpad(hub_entity, dev_id, ok_cmd="Select"):
    def d(cmd): return {"tap_action":send(hub_entity,dev_id,cmd),"hold_action":{"action":"repeat"}}
    return {"type":"dpad","name":"dpad",
            "up":d("DirectionUp"),"down":d("DirectionDown"),
            "left":d("DirectionLeft"),"right":d("DirectionRight"),
            "ok":{"tap_action":send(hub_entity,dev_id,ok_cmd)},"haptics":True}

def vol_row(pid, cids, hub_entity, dev_id):
    """Lautstärke-Reihe als explizite Buttons."""
    row, acts = [], []
    for cid,norm in [("VolumeUp","vol_up"),("Mute","mute"),("VolumeDown","vol_down")]:
        if cid in cids:
            n = f"{pid}_{norm}"
            row.append(n); acts.append(btn(n,cid,hub_entity,dev_id))
    return row, acts

def numpad_rows(pid, cids, hub_entity, dev_id):
    """3×3-Zahlenblock + 0 als Buttons."""
    acts = []
    for n in range(1,10):
        if str(n) in cids: acts.append(btn(f"{pid}_{n}",str(n),hub_entity,dev_id))
    if "0" in cids: acts.append(btn(f"{pid}_zero","0",hub_entity,dev_id))
    rows = [[f"{pid}_1",f"{pid}_2",f"{pid}_3"],
            [f"{pid}_4",f"{pid}_5",f"{pid}_6"],
            [f"{pid}_7",f"{pid}_8",f"{pid}_9"],
            [f"{pid}_zero" if "0" in cids else None]]
    rows = [r for r in rows if any(x and x.split("_")[-1] in [str(i) for i in range(10)]+["zero"] for x in r)]
    return rows, acts

# ── Typ-Erkennung ─────────────────────────────────────────────────────────────
def detect_type(cmds):
    """Geraetetyp aus Command-Set ableiten (reihenfolge-sensibel).

    Marker:
      smart_tv  — Ambilight (eindeutig Philips/Samsung)
      avr       — InputHdmi* + Power + Volume (Receiver)
      satellite — Numpad + Record + Nav (Sky DVR)
      streaming — Apps oder Home+Back ohne Numpad (FireTV/Android)
      fan       — alles andere (einfache Geraete)
    """
    cids = {c["id"] for c in cmds}
    has_nav  = "DirectionUp" in cids
    has_ok   = "OK" in cids or "Select" in cids or "Enter" in cids
    has_num  = "0" in cids
    has_vol  = "VolumeUp" in cids
    has_pow  = "PowerToggle" in cids or "PowerOn" in cids
    has_hdmi = any(c.startswith("InputHdmi") for c in cids)
    has_inp  = sum(1 for c in cids if c.startswith("Input")) >= 3  # viele Eingaenge

    # Ambilight ist eindeutiger Smart-TV-Marker (Philips/Samsung)
    if "Ambilight" in cids or "Netflix" in cids:
        return "smart_tv"
    # AVR: viele Eingaenge + Power + Volume
    if (has_hdmi or has_inp) and has_pow and has_vol:
        return "avr"
    if has_nav and has_ok:
        # Satellite: Numpad + Record (Sky DVR, Kabelreceiver)
        if has_num and ("Record" in cids or "MyPause" in cids):
            return "satellite"
        # Streaming: Apps oder typisches Streaming-Profil (Home+Back, kein Numpad)
        if "Apps" in cids or ("Home" in cids and "Back" in cids and not has_num):
            return "streaming"
    # AVR-Fallback: Power + Volume ohne Nav-spezifische Marker
    if has_pow and has_vol:
        return "avr"
    return "fan"

# ── Templates ─────────────────────────────────────────────────────────────────
def tmpl_streaming(pid, cids, hub_entity, dev_id):
    ok = "OK" if "OK" in cids else "Select"
    acts = [circlepad(hub_entity, dev_id, ok)]
    rows = []
    top = [f"{pid}_{c.lower()}" for c in ("Apps","Home","Menu") if c in cids]
    if top: rows.append(top)
    rows.append([None,"circlepad",None])
    mid = [f"{pid}_{c.lower()}" for c in ("Guide","Exit","Back") if c in cids]
    if mid: rows.append(mid)
    transport = [("SkipBack","skip_back"),("Stop","stop"),("SkipForward","skip_forward"),
                 ("Rewind","rewind"),("Play","play"),("FastForward","fast_forward"),("Pause","pause")]
    tr_have = [(c,n) for c,n in transport if c in cids]
    if tr_have:
        rows.append([None])
        # Gruppieren in 3er-Zeilen
        chunk = [f"{pid}_{n}" for c,n in tr_have[:3]]
        rows.append(chunk)
        if len(tr_have) > 3:
            rows.append([f"{pid}_{n}" for c,n in tr_have[3:]])
    for c in ("Apps","Home","Menu","Guide","Exit","Back"):
        if c in cids: acts.append(btn(f"{pid}_{c.lower()}",c,hub_entity,dev_id))
    for c,n in transport:
        if c in cids: acts.append(btn(f"{pid}_{n}",c,hub_entity,dev_id))
    if "Sleep" in cids: acts.append(btn(f"{pid}_sleep","Sleep",hub_entity,dev_id))
    return rows, acts

def tmpl_satellite(pid, cids, hub_entity, dev_id):
    ok = "Select" if "Select" in cids else "OK"
    acts = [dpad(hub_entity, dev_id, ok)]
    vrow, vacts = vol_row(pid, cids, hub_entity, dev_id)
    acts += vacts
    nrows, nacts = numpad_rows(pid, cids, hub_entity, dev_id)
    acts += nacts
    rows = []
    top = [f"{pid}_power_toggle" if "PowerToggle" in cids else None,
           f"{pid}_home"         if "Home"        in cids else None]
    rows.append([x for x in top if x])
    rows.append([None])
    # Numpad links, Volume rechts nebeneinander
    num_col = [r for r in nrows]
    vol_col = [[v] for v in vrow]
    rows.append([num_col, vol_col])
    rows.append([None])
    rows.append(["dpad"])
    rows.append([None])
    bot = [f"{pid}_{c.lower()}" for c in ("Record","Pause","Back","Stop") if c in cids]
    if bot: rows.append(bot)
    for c in ("PowerToggle","Home","Record","Pause","Back","Stop","Guide"):
        if c in cids: acts.append(btn(f"{pid}_{c.lower()}",c,hub_entity,dev_id))
    return rows, acts

def tmpl_smart_tv(pid, cids, hub_entity, dev_id):
    ok = "OK" if "OK" in cids else "Select"
    acts = [circlepad(hub_entity, dev_id, ok)]
    rows = []
    prow = [f"{pid}_{n}" for c,n in [("PowerToggle","power_toggle"),("PowerOn","power_on"),("PowerOff","power_off")] if c in cids]
    if prow: rows.append(prow)
    rows.append([None])
    top2 = [f"{pid}_{n}" for c,n in [("Ambilight","ambilight"),("Home","home"),("SmartMenu","smart_menu"),("Menu","menu")] if c in cids]
    if top2: rows.append(top2[:3])
    rows.append([None])
    vrow, vacts = vol_row(pid, cids, hub_entity, dev_id)
    acts += vacts
    nrows, nacts = numpad_rows(pid, cids, hub_entity, dev_id)
    acts += nacts
    ch_col = [f"{pid}_{n}" for c,n in [("ChannelUp","ch_up"),("ChannelPrev","ch_prev"),("ChannelDown","ch_down")] if c in cids]
    rows.append([nrows, [vrow, ch_col]])
    rows.append([None])
    mid = [f"{pid}_{n}" for c,n in [("Info","info"),("Exit","exit"),("Options","options")] if c in cids]
    if mid: rows.append(mid)
    rows.append([None,"circlepad",None])
    colors = [f"{pid}_{c.lower()}" for c in ("Red","Green","Yellow","Blue") if c in cids]
    if colors: rows.append(colors)
    if "Play" in cids:
        rows.append([None])
        rows.append([f"{pid}_{n}" for c,n in [("Record","record"),("Play","play"),("Stop","stop")] if c in cids])
        rows.append([f"{pid}_{n}" for c,n in [("Rewind","rewind"),("Pause","pause"),("FastForward","fast_forward")] if c in cids])
    misc = [f"{pid}_{n}" for c,n in [("Subtitle","subtitle"),("Teletext","teletext"),("Guide","guide"),("Back","back")] if c in cids]
    if misc: rows += [[None], misc]
    for c,n in [("PowerToggle","power_toggle"),("PowerOn","power_on"),("PowerOff","power_off"),
                ("Ambilight","ambilight"),("Home","home"),("SmartMenu","smart_menu"),("Menu","menu"),
                ("Info","info"),("Exit","exit"),("Options","options"),
                ("ChannelUp","ch_up"),("ChannelDown","ch_down"),("ChannelPrev","ch_prev"),
                ("Red","red"),("Green","green"),("Yellow","yellow"),("Blue","blue"),
                ("Record","record"),("Play","play"),("Stop","stop"),("Pause","pause"),
                ("Rewind","rewind"),("FastForward","fast_forward"),
                ("Subtitle","subtitle"),("Teletext","teletext"),("Guide","guide"),("Back","back")]:
        if c in cids: acts.append(btn(f"{pid}_{n}",c,hub_entity,dev_id))
    return rows, acts

def tmpl_avr(pid, cids, hub_entity, dev_id):
    acts = []
    rows = []
    prow = [f"{pid}_{n}" for c,n in [("PowerToggle","power_toggle"),("PowerOn","power_on"),("PowerOff","power_off")] if c in cids]
    if prow: rows.append(prow)
    rows.append([None])
    vrow, vacts = vol_row(pid, cids, hub_entity, dev_id)
    acts += vacts; rows.append(vrow)
    if "Play" in cids:
        rows += [[None],[f"{pid}_{n}" for c,n in [("Rewind","rewind"),("Play","play"),("FastForward","fast_forward")] if c in cids],
                 [f"{pid}_{n}" for c,n in [("Stop","stop"),("Pause","pause")] if c in cids]]
    hdmi = [f"{pid}_input_hdmi{i}" for i in range(1,5) if f"InputHdmi{i}" in cids]
    if hdmi: rows += [[None],hdmi]
    for c,n in [("PowerToggle","power_toggle"),("PowerOn","power_on"),("PowerOff","power_off"),
                ("Play","play"),("Stop","stop"),("Pause","pause"),("Rewind","rewind"),("FastForward","fast_forward"),
                ("InputHdmi1","input_hdmi1"),("InputHdmi2","input_hdmi2"),
                ("InputHdmi3","input_hdmi3"),("InputHdmi4","input_hdmi4")]:
        if c in cids: acts.append(btn(f"{pid}_{n}",c,hub_entity,dev_id))
    return rows, acts

def tmpl_fan(pid, cids, hub_entity, dev_id):
    acts, refs = [], []
    for c in sorted(cids):
        n = f"{pid}_{c.lower()}"
        acts.append(btn(n,c,hub_entity,dev_id,label=c)); refs.append(n)
    rows = [refs[i:i+3] for i in range(0,len(refs),3)]
    return rows, acts


# ── Karten-Builder ────────────────────────────────────────────────────────────
def build_device_card(device, hub, hub_entity):
    cmds  = device.get("commands", [])
    cids  = {c["id"] for c in cmds}
    pid   = device["id"]
    bk    = (device.get("backend") or {}).get(hub["backend"], {})
    dev_id = bk.get("device_id") or bk.get("device")
    dtype = detect_type(cmds)
    tmpl  = {"streaming": tmpl_streaming, "satellite": tmpl_satellite,
             "smart_tv":  tmpl_smart_tv,  "avr":       tmpl_avr}.get(dtype, tmpl_fan)
    rows, acts = tmpl(pid, cids, hub_entity, dev_id)
    return {"type": "custom:universal-remote-card", "title": device["name"],
            "platform": "Generic Remote", "remote_id": hub_entity,
            "rows": rows, "custom_actions": acts}

def build_scenario_card(model, hub, hub_entity):
    acts, refs = [], []
    for s in model["scenarios"]:
        if s["hub"] != hub["id"]: continue
        slug = s["id"].split("-")[-1]
        name = f"act_{s['id'].replace('-','_')}"
        refs.append(name)
        activity = (s.get("backend") or {}).get("harmony", {}).get("activity", s["name"])
        acts.append({"type": "button", "name": name, "haptics": True,
                     "icon": SCENARIO_ICONS.get(slug, "mdi:play-circle"),
                     "label": s["name"],
                     "tap_action": {"action": "perform-action",
                                    "perform_action": "remote.turn_on",
                                    "target": {"entity_id": hub_entity},
                                    "data": {"activity": activity}}})
    acts.append({"type": "button", "name": "power", "icon": "mdi:power",
                 "label": "Power Off", "haptics": True,
                 "styles": "ha-icon { color: red; }",
                 "tap_action": {"action": "perform-action",
                                "perform_action": "remote.turn_off",
                                "target": {"entity_id": hub_entity}}})
    return {"type": "custom:universal-remote-card", "platform": "Generic Remote",
            "remote_id": hub_entity, "rows": [["power"], refs],
            "custom_actions": acts, "grid_options": {"columns": "full"}}

def wrap_conditional(hub, device, card):
    sensor = f"binary_sensor.{hub['id']}_show_card_{device['id']}"
    return {"type": "conditional",
            "conditions": [{"entity": sensor, "state": "on"}],
            "card": card}

def build_view(model, hub):
    hub_entity = hub["entity"]
    dev_by_id  = {d["id"]: d for d in model["devices"]}
    seen = []
    for s in model["scenarios"]:
        if s["hub"] != hub["id"]: continue
        for did in s["devices"]:
            if did not in seen and did in dev_by_id: seen.append(did)
    return {
        "title": hub["name"], "path": f"fb-{hub['id']}-gen",
        "icon": "mdi:remote", "subview": False,
        "sections": [
            {"type": "grid", "cards": [build_scenario_card(model, hub, hub_entity)]},
            {"type": "grid", "cards": [
                wrap_conditional(hub, dev_by_id[did],
                                 build_device_card(dev_by_id[did], hub, hub_entity))
                for did in seen]},
        ]}

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="Modell -> Lovelace-YAML (URC, P3-conditional)")
    ap.add_argument("--model", required=True)
    ap.add_argument("--out",   required=True)
    a = ap.parse_args()
    model = json.load(open(a.model, encoding="utf-8"))
    views = [build_view(model, h) for h in model["hubs"]]
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write("# Generiert von generator/build_cards.py\n# NICHT manuell editieren\n\n")
        yaml.dump({"views": views}, f, allow_unicode=True,
                  sort_keys=False, default_flow_style=False)
    for v in views:
        n = sum(len(s["cards"]) for s in v.get("sections", [])[1:])
        print(f"OK: {a.out} — '{v['title']}': {n} Geraete-Karten (URC, sections, P3-conditional)")

if __name__ == "__main__":
    main()
