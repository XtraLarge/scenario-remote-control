#!/usr/bin/env python3
"""build_cards.py — Modell → Lovelace-YAML (custom:universal-remote-card).
Erzeugt sections-View + Gradient-CSS + Template-Binary-Sensors."""
import argparse, json, os, sys
try:
    import yaml
except ImportError:
    sys.exit("FEHLER: pip install pyyaml")

# ── Design ────────────────────────────────────────────────────────────────────
DEVICE_ACCENT = {
    "smart_tv":  "#22c55e",
    "satellite": "#c4b5fd",
    "streaming": "#fb923c",
    "avr":       "#60a5fa",
    "fan":       "#94a3b8",
}

def card_styles(accent="#888888"):
    return (
        f":host ha-card{{\n  --accent: {accent};\n}}\n"
        ":host ha-card{\n"
        "  --bg:  var(--ha-card-background, var(--card-background-color, #1c1c1c));\n"
        "  --txt: var(--primary-text-color);\n"
        "  --gw: 2px; --gr: 12px;\n"
        "  --stroke: color-mix(in oklab, var(--txt) 65%, transparent);\n"
        "  background: linear-gradient(\n"
        "    135deg,\n"
        "    color-mix(in oklab, var(--bg) 88%, var(--accent) 12%),\n"
        "    color-mix(in oklab, var(--bg) 72%, var(--accent) 28%)\n"
        "  ) !important;\n"
        "  border-radius: var(--gr);\n"
        "  padding: 8px;\n"
        "  box-shadow:\n"
        "    inset 0 0 0 var(--gw) var(--stroke),\n"
        "    0 4px 12px rgba(0,0,0,.12);\n"
        "}\n"
    )

# ── Icons / Labels ────────────────────────────────────────────────────────────
ICONS = {
    "PowerOn":"mdi:power-on","PowerOff":"mdi:power-off","PowerToggle":"mdi:power",
    "VolumeUp":"mdi:volume-high","VolumeDown":"mdi:volume-medium","Mute":"mdi:volume-off",
    "ChannelUp":"mdi:chevron-up-box","ChannelDown":"mdi:chevron-down-box",
    "ChannelPrev":"mdi:arrow-u-left-top",
    "DirectionUp":"mdi:arrow-up","DirectionDown":"mdi:arrow-down",
    "DirectionLeft":"mdi:arrow-left","DirectionRight":"mdi:arrow-right",
    "OK":"mdi:circle-small","Select":"mdi:circle-small",
    "Back":"mdi:keyboard-return","Exit":"mdi:exit-to-app",
    "Menu":"mdi:menu","Home":"mdi:home-outline",
    "Guide":"mdi:television-guide","Info":"mdi:information-outline",
    "Play":"mdi:play-circle-outline","Pause":"mdi:pause-circle-outline",
    "Stop":"mdi:stop-circle-outline",
    "Rewind":"mdi:rewind","FastForward":"mdi:fast-forward",
    "SkipBack":"mdi:skip-previous","SkipForward":"mdi:skip-next",
    "Record":"mdi:record-circle-outline","Delete":"mdi:delete-outline",
    "Apps":"mdi:apps","Netflix":"mdi:netflix",
    "Settings":"mdi:cog-outline","Sleep":"mdi:sleep",
    "Subtitle":"mdi:subtitles-outline","Teletext":"mdi:book-outline",
    "Ambilight":"mdi:led-strip-variant","SmartMenu":"mdi:star-outline",
    "List":"mdi:format-list-bulleted","Options":"mdi:tools",
    "Green":"mdi:alpha-g-circle","Red":"mdi:alpha-r-circle",
    "Yellow":"mdi:alpha-y-circle","Blue":"mdi:alpha-b-circle",
    "InputHdmi1":"mdi:hdmi-port","InputHdmi2":"mdi:hdmi-port",
    "InputHdmi3":"mdi:hdmi-port","InputHdmi4":"mdi:hdmi-port",
    **{str(n): f"mdi:numeric-{n}" for n in range(10)},
}
ICON_COLORS = {
    "Green":"color:green","Red":"color:red",
    "Yellow":"color:#f59e0b","Blue":"color:dodgerblue",
}
SCENARIO_LABELS = {
    "sky":"Sky","firetv":"Fire TV","android":"Android TV","bluetooth":"Bluetooth",
    "radio":"Radio","ps":"PlayStation","netflix":"Netflix","kodi":"Kodi",
    "youtube":"YouTube","appletv":"Apple TV","chromecast":"Chromecast",
    "xbox":"Xbox","switch":"Nintendo Switch",
}
SCENARIO_ICONS = {
    "sky":"mdi:satellite-uplink","firetv":"mdi:television-play","android":"mdi:android",
    "bluetooth":"mdi:bluetooth","radio":"mdi:radio","ps":"mdi:sony-playstation",
    "netflix":"mdi:netflix","kodi":"mdi:kodi","youtube":"mdi:youtube",
    "appletv":"mdi:apple","chromecast":"mdi:cast","xbox":"mdi:microsoft-xbox",
    "switch":"mdi:nintendo-switch",
}
LABELS = {
    "PowerOn":"An","PowerOff":"Aus","PowerToggle":"Power",
    "VolumeUp":"Vol+","VolumeDown":"Vol-","Mute":"Stumm",
    "ChannelUp":"Ch+","ChannelDown":"Ch-","ChannelPrev":"Prev",
    "DirectionUp":"","DirectionDown":"","DirectionLeft":"","DirectionRight":"",
    "OK":"OK","Select":"OK","Back":"Back","Exit":"Exit",
    "Menu":"Menu","Home":"Home","Guide":"Guide","Info":"Info","Options":"…",
    "Play":"Play","Pause":"Pause","Stop":"Stop",
    "Rewind":"◀◀","FastForward":"▶▶","SkipBack":"⏮","SkipForward":"⏭",
    "Record":"Rec","Delete":"Del","Apps":"Apps","Sleep":"Sleep",
    "Subtitle":"Untertitel","Teletext":"Teletext",
    "Ambilight":"Ambilight","SmartMenu":"SmartMenu",
    "List":"Liste","Options":"…",
    "Green":"Grün","Red":"Rot","Yellow":"Gelb","Blue":"Blau",
    "InputHdmi1":"HDMI 1","InputHdmi2":"HDMI 2",
    "InputHdmi3":"HDMI 3","InputHdmi4":"HDMI 4",
    **{str(n): str(n) for n in range(10)},
}

# ── Helfer ────────────────────────────────────────────────────────────────────
def ic(cmd_id): return ICONS.get(cmd_id)
def send(hub_entity, dev_id, cmd_id):
    return {"action":"perform-action","perform_action":"remote.send_command",
            "target":{"entity_id":hub_entity},"data":{"device":dev_id,"command":cmd_id}}

def btn(name, cmd_id, hub_entity, dev_id, label=None, repeat=False):
    b = {"type":"button","name":name,"tap_action":send(hub_entity,dev_id,cmd_id),"haptics":True}
    i = ic(cmd_id)
    if i: b["icon"] = i
    b["label"] = label if label is not None else LABELS.get(cmd_id, cmd_id)
    if repeat: b["hold_action"] = {"action":"repeat"}
    col = ICON_COLORS.get(cmd_id)
    if col: b["icon_style"] = col
    return b

def clean_rows(rows):
    """None-Spacer zwischen Gruppen behalten; reine None-Zeilen am Ende entfernen.
    None INNERHALB einer Zeile bleibt (für Zentrierung, z.B. [None, circlepad, None])."""
    out = []
    for row in rows:
        if isinstance(row, list):
            # Mindestens ein nicht-None? → Zeile behalten (inkl. None für Zentrierung)
            if any(item is not None if not isinstance(item, list) else True for item in row):
                out.append(row)
        else:
            out.append([None])  # Spacer-Zeile: [None] statt bare null (URC-kompatibel)
    while out and out[-1] is None:
        out.pop()
    return out

def vol_row(pid, cids, hub_entity, dev_id):
    row, acts = [], []
    for cid,nm in [("VolumeUp","vol_up"),("Mute","mute"),("VolumeDown","vol_down")]:
        if cid in cids:
            n = f"{pid}_{nm}"; row.append(n)
            acts.append(btn(n, cid, hub_entity, dev_id))
    return row, acts

def numpad_rows(pid, cids, hub_entity, dev_id):
    """3×3 Ziffernblock + 0."""
    acts = []
    for n in list(range(1,10)) + [0]:
        if str(n) in cids:
            acts.append(btn(f"{pid}_num_{n}", str(n), hub_entity, dev_id, label=str(n)))
    rows = []
    for trio in [(1,2,3),(4,5,6),(7,8,9)]:
        r = [f"{pid}_num_{n}" for n in trio if str(n) in cids]
        if r: rows.append(r)
    if "0" in cids: rows.append([f"{pid}_num_0"])
    return rows, acts

def circlepad_action(pid, cids, hub_entity, dev_id, ok_cmd=None):
    """circlepad als URC-Action (type:circlepad)."""
    ok = ok_cmd or ("OK" if "OK" in cids else "Select" if "Select" in cids else "OK")
    def d(cmd): return {"tap_action":send(hub_entity,dev_id,cmd),"hold_action":{"action":"repeat"}}
    return {"type":"circlepad","name":f"{pid}_circlepad",
            "tap_action":send(hub_entity,dev_id,ok),
            "up":{**d("DirectionUp"),"icon":"mdi:chevron-up"},
            "down":{**d("DirectionDown"),"icon":"mdi:chevron-down"},
            "left":{**d("DirectionLeft"),"icon":"mdi:chevron-left"},
            "right":{**d("DirectionRight"),"icon":"mdi:chevron-right"},
            "haptics":True}

def detect_type(cmds):
    cids = {c["id"] for c in cmds}
    has_nav="DirectionUp" in cids; has_num="0" in cids; has_vol="VolumeUp" in cids
    has_pow="PowerToggle" in cids or "PowerOn" in cids
    has_hdmi=any(c.startswith("InputHdmi") for c in cids)
    has_inp=sum(1 for c in cids if c.startswith("Input"))>=3
    if "Ambilight" in cids or "SmartMenu" in cids: return "smart_tv"
    if (has_hdmi or has_inp) and has_pow and has_vol: return "avr"
    if has_nav:
        if has_num and ("Record" in cids or "MyPause" in cids): return "satellite"
        if "Apps" in cids or ("Home" in cids and "Back" in cids and not has_num): return "streaming"
    if has_pow and has_vol: return "avr"
    return "fan"

# ── Templates ─────────────────────────────────────────────────────────────────
def tmpl_smart_tv(pid, cids, hub_entity, dev_id, accent=None):
    acts, rows = [], []
    prow=[f"{pid}_{n}" for c,n in [("PowerToggle","pwr"),("PowerOn","pwr_on"),("PowerOff","pwr_off")] if c in cids]
    if prow: rows.append(prow); rows.append(None)
    top=[f"{pid}_{n}" for c,n in [("Ambilight","ambilight"),("Home","home"),("SmartMenu","smart_menu")] if c in cids]
    if top: rows.append(top); rows.append(None)
    # Numpad + Volume nebeneinander
    nrows,nacts=numpad_rows(pid,cids,hub_entity,dev_id); acts+=nacts
    vrow,vacts=vol_row(pid,cids,hub_entity,dev_id); acts+=vacts
    if nrows and vrow:
        rows.append([nrows[0]+[f"{pid}_num_0" if "0" in cids else None], vrow])
        for nr in nrows[1:]: rows.append(nr)
        rows.append(None)
    elif nrows:
        rows+=nrows; rows.append(None)
    elif vrow:
        rows.append(vrow); rows.append(None)
    # Info/Exit/Options
    mid=[f"{pid}_{n}" for c,n in [("Info","info"),("Exit","exit"),("Options","options")] if c in cids]
    if mid: rows.append(mid)
    # Channel-Prev + Circlepad + Channel-Up/Down nebeneinander
    has_nav=all(c in cids for c in ("DirectionUp","DirectionLeft","DirectionRight","DirectionDown"))
    ch_ud=[f"{pid}_{n}" for c,n in [("ChannelUp","ch_up"),("List","list"),("ChannelDown","ch_down")] if c in cids]
    if has_nav:
        cp=circlepad_action(pid,cids,hub_entity,dev_id); acts.append(cp)
        ch_prev=f"{pid}_ch_prev" if "ChannelPrev" in cids else None
        mid_row=[ch_prev, f"{pid}_circlepad", ch_ud if ch_ud else None]
        rows.append(mid_row)
        rows.append(None)
    # Misc: teletext/subtitle/guide/back
    misc=[f"{pid}_{n}" for c,n in [("Teletext","teletext"),("Subtitle","subtitle"),("Guide","guide"),("Back","back")] if c in cids]
    if misc: rows.append(misc); rows.append(None)
    # Transport
    if "Play" in cids:
        rows.append([f"{pid}_{n}" for c,n in [("Record","record"),("Play","play")] if c in cids])
        rows.append([f"{pid}_{n}" for c,n in [("Rewind","rewind"),("Stop","stop"),("FastForward","ffw")] if c in cids])
        rows.append([f"{pid}_{n}" for c,n in [("Pause","pause")] if c in cids])
        rows.append(None)
    # Farbtasten
    colors=[f"{pid}_{c.lower()}" for c in ("Red","Green","Yellow","Blue") if c in cids]
    if colors: rows.append(colors)
    # Alle Button-Definitionen
    for c,n in [("PowerToggle","pwr"),("PowerOn","pwr_on"),("PowerOff","pwr_off"),
                ("Ambilight","ambilight"),("Home","home"),("SmartMenu","smart_menu"),
                ("Info","info"),("Exit","exit"),("Options","options"),
                ("ChannelUp","ch_up"),("ChannelDown","ch_down"),("ChannelPrev","ch_prev"),
                ("List","list"),
                ("Red","red"),("Green","green"),("Yellow","yellow"),("Blue","blue"),
                ("Record","record"),("Play","play"),("Stop","stop"),("Pause","pause"),
                ("Rewind","rewind"),("FastForward","ffw"),
                ("Teletext","teletext"),("Subtitle","subtitle"),("Guide","guide"),("Back","back")]:
        if c in cids: acts.append(btn(f"{pid}_{n}",c,hub_entity,dev_id))
    return clean_rows(rows), acts

def tmpl_satellite(pid, cids, hub_entity, dev_id, accent=None):
    acts, rows = [], []
    prow=[f"{pid}_{n}" for c,n in [("PowerToggle","pwr"),("Home","home")] if c in cids]
    if prow: rows.append(prow); rows.append(None)
    nrows,nacts=numpad_rows(pid,cids,hub_entity,dev_id); acts+=nacts
    vrow,vacts=vol_row(pid,cids,hub_entity,dev_id); acts+=vacts
    if nrows and vrow:
        rows.append([nrows[0]+[f"{pid}_num_0" if "0" in cids else None], vrow])
        for nr in nrows[1:]: rows.append(nr)
    elif nrows: rows+=nrows
    if vrow and not nrows: rows.append(vrow)
    rows.append(None)
    has_nav=all(c in cids for c in ("DirectionUp","DirectionLeft","DirectionRight","DirectionDown"))
    if has_nav:
        cp=circlepad_action(pid,cids,hub_entity,dev_id,"Select"); acts.append(cp)
        rows.append([None, f"{pid}_circlepad", None]); rows.append(None)
    transp=[f"{pid}_{n}" for c,n in [("Record","record"),("Pause","pause"),("Back","back")] if c in cids]
    if transp: rows.append(transp)
    for c,n in [("PowerToggle","pwr"),("Home","home"),("Record","record"),("Pause","pause"),("Back","back")]:
        if c in cids: acts.append(btn(f"{pid}_{n}",c,hub_entity,dev_id))
    return clean_rows(rows), acts

def tmpl_streaming(pid, cids, hub_entity, dev_id, accent=None):
    ok="OK" if "OK" in cids else "Select"
    acts, rows = [], []
    top=[f"{pid}_{n}" for c,n in [("Apps","apps"),("Home","home"),("Menu","menu")] if c in cids]
    if top: rows.append(top); rows.append(None)
    has_nav=all(c in cids for c in ("DirectionUp","DirectionLeft","DirectionRight","DirectionDown"))
    if has_nav:
        cp=circlepad_action(pid,cids,hub_entity,dev_id,ok); acts.append(cp)
        rows.append([None, f"{pid}_circlepad", None]); rows.append(None)
    nav2=[f"{pid}_{n}" for c,n in [("Guide","guide"),("Exit","exit"),("Back","back")] if c in cids]
    if nav2: rows.append(nav2); rows.append(None)
    t1=[f"{pid}_{n}" for c,n in [("SkipBack","skip_back"),("Stop","stop"),("SkipForward","skip_fwd")] if c in cids]
    if t1: rows.append(t1)
    t2=[f"{pid}_{n}" for c,n in [("Rewind","rewind"),("Play","play"),("FastForward","ffw"),("Pause","pause")] if c in cids]
    if t2: rows.append(t2)
    for c,n in [("Apps","apps"),("Home","home"),("Menu","menu"),("Guide","guide"),("Exit","exit"),("Back","back"),
                ("SkipBack","skip_back"),("Stop","stop"),("SkipForward","skip_fwd"),
                ("Rewind","rewind"),("Play","play"),("FastForward","ffw"),("Pause","pause")]:
        if c in cids: acts.append(btn(f"{pid}_{n}",c,hub_entity,dev_id))
    return clean_rows(rows), acts

def tmpl_avr(pid, cids, hub_entity, dev_id, accent=None):
    acts, rows = [], []
    prow=[f"{pid}_{n}" for c,n in [("PowerToggle","pwr"),("PowerOn","pwr_on"),("PowerOff","pwr_off")] if c in cids]
    if prow: rows.append(prow); rows.append(None)
    vrow,vacts=vol_row(pid,cids,hub_entity,dev_id); acts+=vacts
    if vrow: rows.append(vrow); rows.append(None)
    if "Play" in cids:
        rows.append([f"{pid}_{n}" for c,n in [("Rewind","rewind"),("Play","play"),("FastForward","ffw")] if c in cids])
        rows.append([f"{pid}_{n}" for c,n in [("Stop","stop"),("Pause","pause")] if c in cids])
        rows.append(None)
    hdmi=[f"{pid}_hdmi{i}" for i in range(1,5) if f"InputHdmi{i}" in cids]
    if hdmi: rows.append(hdmi)
    for c,n in [("PowerToggle","pwr"),("PowerOn","pwr_on"),("PowerOff","pwr_off"),
                ("Play","play"),("Stop","stop"),("Pause","pause"),("Rewind","rewind"),("FastForward","ffw"),
                ("InputHdmi1","hdmi1"),("InputHdmi2","hdmi2"),("InputHdmi3","hdmi3"),("InputHdmi4","hdmi4")]:
        if c in cids: acts.append(btn(f"{pid}_{n}",c,hub_entity,dev_id))
    return clean_rows(rows), acts

def tmpl_fan(pid, cids, hub_entity, dev_id, accent=None):
    acts, refs = [], []
    for c in sorted(cids):
        n=f"{pid}_{c.lower()}"; acts.append(btn(n,c,hub_entity,dev_id,label=LABELS.get(c,c))); refs.append(n)
    return [refs[i:i+3] for i in range(0,len(refs),3)], acts

# ── Karten / View ─────────────────────────────────────────────────────────────
def build_device_card(device, hub, hub_entity):
    cmds=device.get("commands",[]); cids={c["id"] for c in cmds}; pid=device["id"]
    bk=(device.get("backend") or {}).get(hub["backend"],{})
    dev_id=bk.get("device_id") or bk.get("device")
    dtype=detect_type(cmds)
    accent=device.get("accent_color") or DEVICE_ACCENT.get(dtype,"#888")
    tmpl={"streaming":tmpl_streaming,"satellite":tmpl_satellite,
          "smart_tv":tmpl_smart_tv,"avr":tmpl_avr}.get(dtype,tmpl_fan)
    rows,acts=tmpl(pid,cids,hub_entity,dev_id,accent=accent)
    return {"type":"custom:universal-remote-card","title":device["name"],
            "entity":hub_entity,"rows":rows,"custom_actions":acts,
            "styles":card_styles(accent)}

def build_scenario_card(model, hub, hub_entity, overrides=None):
    acts, refs = [], []
    ov=overrides or {}
    for s in model["scenarios"]:
        if s["hub"]!=hub["id"]: continue
        raw_slug=s["id"].split("-")[-1]; slug=raw_slug.replace(f"{hub['id']}_","")
        name=f"act_{s['id'].replace('-','_')}"; refs.append(name)
        activity=(s.get("backend") or {}).get("harmony",{}).get("activity",s["name"])
        raw=s["name"]
        short=SCENARIO_LABELS.get(slug) or (raw.split(None,1)[-1].title() if " " in raw else raw.title())
        label=ov.get(s["id"],{}).get("label") or short
        icon=ov.get(s["id"],{}).get("icon") or SCENARIO_ICONS.get(slug,"mdi:play-circle")
        acts.append({"type":"button","name":name,"haptics":True,"icon":icon,"label":label,
                     "tap_action":{"action":"perform-action","perform_action":"remote.turn_on",
                                   "target":{"entity_id":hub_entity},"data":{"activity":activity}}})
    acts.append({"type":"button","name":"power_off","icon":"mdi:power","label":"Aus",
                 "haptics":True,"icon_style":"color:red",
                 "tap_action":{"action":"perform-action","perform_action":"remote.turn_off",
                               "target":{"entity_id":hub_entity}}})
    # Aktivitäts-Buttons in Zeilen à max 4 aufteilen (verhindert Overflow)
    # power_off steht bereits in all_rows[0] – NICHT nochmal in refs anhängen
    COLS = 4
    act_rows = [refs[i:i+COLS] for i in range(0, len(refs), COLS)]
    all_rows = [["power_off"]] + act_rows
    return {"type":"custom:universal-remote-card","entity":hub_entity,
            "rows":all_rows,"custom_actions":acts,
            "styles":card_styles("#ef4444")}

def activity_conditions(device_id, model, hub):
    """OR-Conditions direkt auf remote.current_activity — kein extra Sensor nötig.
    Der echte Bug war bare null in URC-rows (jetzt [None]), nicht das Condition-Format."""
    hub_id=hub["id"]; hub_entity=hub["entity"]
    acts=[]
    for s in model["scenarios"]:
        if s["hub"]!=hub_id: continue
        if device_id in s.get("devices",[]):
            act=(s.get("backend") or {}).get("harmony",{}).get("activity",s["name"])
            if act not in acts: acts.append(act)
    if not acts:
        return [{"entity":hub_entity,"state":"on"}]
    if len(acts)==1:
        return [{"condition":"state","entity":hub_entity,
                 "attribute":"current_activity","state":acts[0]}]
    return [{"condition":"or","conditions":[
        {"condition":"state","entity":hub_entity,
         "attribute":"current_activity","state":a} for a in acts]}]

def wrap_conditional(device, hub_id, card, model=None, hub=None):
    """Wickelt FB-Karte in conditional mit OR-Conditions auf remote.current_activity.
    Kein extra Sensor nötig — der Bug war bare null in URC-rows, nicht das Condition-Format."""
    if model and hub:
        conds = activity_conditions(device["id"], model, hub)
    else:
        conds = [{"entity": hub["entity"], "state": "on"}]
    return {"type":"conditional","conditions":conds,
            "card":{"type":"vertical-stack","cards":[card]}}

def build_view(model, hub, overrides=None):
    hub_entity=hub["entity"]; hub_id=hub["id"]
    dev_by_id={d["id"]:d for d in model["devices"]}
    seen_set=set()
    for s in model["scenarios"]:
        if s["hub"]!=hub_id: continue
        for did in s.get("devices",[]):
            if did in dev_by_id: seen_set.add(did)
    seen=sorted(seen_set, key=lambda did:(dev_by_id[did].get("order",999),did))

    # Sections-View: Scenario oben (volle Breite), danach pro Gerät eine Section
    scenario_section={
        "type":"grid","column_span":4,
        "cards":[build_scenario_card(model,hub,hub_entity,overrides)]
    }
    dev_sections=[]
    for did in seen:
        dev=dev_by_id[did]
        card=wrap_conditional(dev, hub_id, build_device_card(dev,hub,hub_entity), model=model, hub=hub)
        dev_sections.append({"type":"grid","cards":[card]})

    return {"type":"sections","max_columns":4,
            "title":hub["name"],"path":f"fb-{hub_id}-gen",
            "icon":"mdi:remote","subview":False,
            "sections":[scenario_section]+dev_sections}

def load_scenario_overrides(model_path):
    p=model_path.replace(".model.json",".scenarios.json")
    if os.path.exists(p):
        raw=json.load(open(p,encoding="utf-8"))
        if isinstance(raw,list): return {s["id"]:s for s in raw if s.get("icon") or s.get("label")}
        return raw
    return {}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--model",default="data/local/wz.model.json")
    p.add_argument("--out",default="cards/local/wz.yaml")
    args=p.parse_args()
    model=json.load(open(args.model,encoding="utf-8"))
    overrides=load_scenario_overrides(args.model)
    views=[]
    for hub in model["hubs"]:
        views.append(build_view(model,hub,overrides))
    os.makedirs(os.path.dirname(args.out),exist_ok=True)
    with open(args.out,"w",encoding="utf-8") as f:
        yaml.dump({"views":views},f,allow_unicode=True,sort_keys=False)
    print(f"✓ {args.out}")
    print("  → Conditions direkt auf remote.current_activity (kein extra Sensor nötig)")

if __name__=="__main__":
    main()
