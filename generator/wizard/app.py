#!/usr/bin/env python3
"""Remote Config Wizard — Flask-App (Port 8777).

Schritt 1: Quelle wählen + Conf-Datei + Roster (welche FBs je Activity)
Schritt 2: Layout je FB (P4, Placeholder)
Schritt 3: Generieren (Modell + Karte)

Läuft auf Manage; per HA panel_iframe einbindbar.
"""
import json, os, glob, subprocess, sys
from flask import Flask, render_template, request, jsonify, redirect, url_for

# Pfade relativ zum Repo-Root (zwei Ebenen über wizard/)
REPO   = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LOCAL  = os.path.join(REPO, "data", "local")
GEN    = os.path.join(REPO, "generator")
CARDS  = os.path.join(REPO, "cards", "local")

app = Flask(__name__, template_folder="templates", static_folder="static")

# ── Hilfsfunktionen ──────────────────────────────────────────────────────────
def list_confs():
    return sorted(os.path.basename(f) for f in glob.glob(os.path.join(LOCAL, "harmony_*.conf")))

def list_configured_rooms():
    """Bereits konfigurierte Räume aus data/local/*.model.json."""
    rooms = []
    for f in sorted(glob.glob(os.path.join(LOCAL, "*.model.json"))):
        room_id = os.path.basename(f).replace(".model.json", "")
        try:
            with open(f, encoding="utf-8") as fh:
                m = json.load(fh)
            hubs = m.get("hubs", [])
            hub  = hubs[0] if hubs else {}
            rooms.append({
                "id":         room_id,
                "name":       hub.get("name", room_id.upper()),
                "hub_entity": hub.get("entity", ""),
                "conf_name":  "",   # wird in room-config live ermittelt
                "devices":    len(m.get("devices", [])),
                "activities": len(m.get("scenarios", [])),
            })
        except Exception:
            pass
    return rooms


def load_harmony(filename):
    path = os.path.join(LOCAL, filename)
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def hub_id_from_conf_name(filename):
    """harmony_<HUB-ID>.conf → <HUB-ID>"""
    return filename.replace("harmony_","").replace(".conf","")

# ── Routen ───────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    confs  = list_confs()
    rooms  = list_configured_rooms()
    return render_template("step1.html", conf_files=confs, configured_rooms=rooms)

@app.route("/api/room-config/<room_id>")
def api_room_config(room_id):
    """Gespeicherte Konfiguration eines Raums zurückgeben (für Vorauswahl)."""
    model_path = os.path.join(LOCAL, f"{room_id}.model.json")
    map_path   = os.path.join(LOCAL, f"{room_id}.map.json")
    if not os.path.exists(model_path):
        return jsonify({"error": "Kein Modell gefunden"}), 404
    with open(model_path, encoding="utf-8") as f:
        model = json.load(f)

    # Modell-Struktur: hubs[] statt hub{}
    hubs       = model.get("hubs", [])
    hub        = hubs[0] if hubs else {}
    hub_entity = hub.get("entity", "")
    room_name  = hub.get("name", room_id.upper())

    # conf_name aus map.json (dort beim Generieren gespeichert) oder auto-detect
    conf_name = ""
    if os.path.exists(map_path):
        with open(map_path, encoding="utf-8") as f:
            mp = json.load(f)
        conf_name = mp.get("conf_name", "")
        if not conf_name:
            # Fallback: harmony_*.conf nach Geräte-Übereinstimmung suchen
            map_devs = set(mp.get("devices", {}).keys())
            for cf in list_confs():
                try:
                    hconf = load_harmony(cf)
                    cdevs = set(hconf.get("Devices", {}).keys())
                    if map_devs and map_devs.issubset(cdevs | {d.lower() for d in cdevs}):
                        conf_name = cf; break
                    if len(map_devs & cdevs) >= max(1, len(map_devs) // 2):
                        conf_name = cf; break
                except Exception:
                    pass

    # Geräte-ID → Geräte-Name (Harmony-Name, wie in renderRoster data-dev)
    dev_names = {d["id"]: d.get("name", d["id"]) for d in model.get("devices", [])}

    # Roster: activity-NAME → [device-NAME] (passt zu data-act/data-dev im JS)
    # Quelle: map.json (scenarios nach Harmony-Aktivitätsname gegliedert)
    roster = {}
    if os.path.exists(map_path):
        with open(map_path, encoding="utf-8") as fmp:
            mp = json.load(fmp)
        for act_name, s in mp.get("scenarios", {}).items():
            devs = [dev_names.get(d, d) for d in s.get("devices", [])]
            roster[act_name] = devs
    else:
        # Fallback: model.json scenarios (name statt ID)
        for s in model.get("scenarios", []):
            act_name = s.get("name", s.get("id", ""))
            devs = [dev_names.get(d, d) for d in s.get("devices", [])]
            if act_name:
                roster[act_name] = devs

    return jsonify({
        "room_id":    room_id,
        "room_name":  room_name,
        "hub_entity": hub_entity,
        "conf_name":  conf_name,
        "roster":     roster,
    })

@app.route("/api/load-conf", methods=["POST"])
def api_load_conf():
    """Harmony-Conf einlesen → Activities + Devices zurückgeben."""
    data = request.json or {}
    conf_name = data.get("conf", "")
    if not conf_name or "/" in conf_name:
        return jsonify({"error": "ungültiger Dateiname"}), 400
    try:
        conf = load_harmony(conf_name)
    except FileNotFoundError:
        return jsonify({"error": "Datei nicht gefunden"}), 404

    activities = {
        str(aid): name
        for aid, name in conf.get("Activities", {}).items()
        if name.strip().upper() != "POWEROFF"
    }
    devices = [
        {"name": name, "harmony_id": info.get("id"), "cmd_count": len(info.get("commands", []))}
        for name, info in conf.get("Devices", {}).items()
    ]
    return jsonify({"activities": activities, "devices": devices})

@app.route("/api/generate", methods=["POST"])
def api_generate():
    """Roster + Metadaten → map.json → Modell → Karte generieren."""
    data = request.json or {}
    conf_name  = data.get("conf", "")
    hub_entity = data.get("hub_entity", "").strip()
    room_id    = data.get("room_id", "").strip().lower()
    room_name  = data.get("room_name", room_id).strip()
    roster     = data.get("roster", {})      # {activity_id: [device_name, ...]}
    dev_labels = data.get("dev_labels", {})  # {device_name: display_label}

    if not all([conf_name, hub_entity, room_id, roster]):
        return jsonify({"error": "Fehlende Pflichtfelder"}), 400
    if "/" in conf_name or "/" in room_id:
        return jsonify({"error": "ungültige Eingabe"}), 400

    try:
        conf = load_harmony(conf_name)
    except FileNotFoundError:
        return jsonify({"error": "Conf nicht gefunden"}), 404

    # device_id-Mapping: Harmony-Name → numerische ID
    dev_id_map = {name: info.get("id") for name, info in conf.get("Devices", {}).items()}

    # Map-Datei aufbauen
    hub_map = {"id": room_id, "name": room_name, "backend": "harmony", "entity": hub_entity}

    devices_map = {}
    for dev_name in conf.get("Devices", {}):
        label = dev_labels.get(dev_name, dev_name)
        slug  = label.lower().replace(" ", "_").replace("-", "_")[:20]
        devices_map[dev_name] = {"id": slug, "name": label}

    # Alle in irgendeinem Roster genutzten Device-Namen
    used_devs = {dn for devs in roster.values() for dn in devs}

    # Scenarios aus Roster aufbauen
    scenarios_map = {}
    act_names = conf.get("Activities", {})
    for act_id, act_name in act_names.items():
        act_name = act_name.strip()
        if act_name.upper() == "POWEROFF":
            continue
        devs_in = roster.get(act_id, [])
        if not devs_in:
            continue  # Activity ohne Roster überspringen
        slug = act_name.lower().replace(" ", "_").replace("-","_")
        dev_ids = [devices_map[d]["id"] for d in devs_in if d in devices_map]
        primary = dev_ids[0] if dev_ids else None
        scenarios_map[act_name] = {
            "id":            f"{room_id}-{slug}",
            "name":          act_name,
            "primaryDevice": primary,
            "devices":       dev_ids,
        }

    full_map = {
        "hub":       hub_map,
        "devices":   {k: v for k, v in devices_map.items() if k in used_devs},
        "scenarios": scenarios_map,
    }

    # map.json schreiben
    os.makedirs(LOCAL, exist_ok=True)
    map_path   = os.path.join(LOCAL, f"{room_id}.map.json")
    model_path = os.path.join(LOCAL, f"{room_id}.model.json")
    card_path  = os.path.join(CARDS, f"{room_id}.yaml")
    os.makedirs(CARDS, exist_ok=True)

    with open(map_path, "w", encoding="utf-8") as f:
        json.dump(full_map, f, indent=2, ensure_ascii=False)

    # extract_harmony.py ausführen
    conf_path = os.path.join(LOCAL, conf_name)
    r1 = subprocess.run(
        [sys.executable, os.path.join(GEN, "extract_harmony.py"),
         "--conf", conf_path, "--map", map_path, "--out", model_path],
        capture_output=True, text=True, cwd=REPO)
    if r1.returncode != 0:
        return jsonify({"error": "extract_harmony fehlgeschlagen", "detail": r1.stderr}), 500

    # build_cards.py ausführen
    r2 = subprocess.run(
        [sys.executable, os.path.join(GEN, "build_cards.py"),
         "--model", model_path, "--out", card_path],
        capture_output=True, text=True, cwd=REPO)
    if r2.returncode != 0:
        return jsonify({"error": "build_cards fehlgeschlagen", "detail": r2.stderr}), 500

    # Ergebnis lesen
    model = json.load(open(model_path, encoding="utf-8"))
    return jsonify({
        "ok": True,
        "model_path": model_path,
        "card_path":  card_path,
        "devices":    len(model["devices"]),
        "scenarios":  len(model["scenarios"]),
        "stdout_extract": r1.stdout.strip(),
        "stdout_cards":   r2.stdout.strip(),
    })

# ── Schritt 2: Layout-Editor ─────────────────────────────────────────────────
@app.route("/editor/<room_id>")
def editor(room_id):
    """Visueller FB-Layout-Editor für ein generiertes Modell."""
    model_path = os.path.join(LOCAL, f"{room_id}.model.json")
    if not os.path.exists(model_path):
        return f"Modell {room_id}.model.json nicht gefunden. Bitte zuerst Schritt 1 ausführen.", 404
    model = json.load(open(model_path, encoding="utf-8"))
    return render_template("editor.html", model=model, room_id=room_id)

@app.route("/api/mdi-search")
def mdi_search():
    """MDI-Icon-Suche — alle 7000+ Icons aus mdi-all.json."""
    import os as _os
    q        = request.args.get("q", "").lower().replace("mdi:","")
    max_n    = int(request.args.get("n", 120))
    json_path = _os.path.join(_os.path.dirname(__file__), "static", "mdi-all.json")
    if _os.path.exists(json_path):
        import json as _json
        all_icons = _json.load(open(json_path))
    else:
        all_icons = ["mdi:power","mdi:home","mdi:play","mdi:pause","mdi:stop",
                     "mdi:volume-plus","mdi:volume-minus","mdi:volume-mute","mdi:menu"]
    if q:
        # Ranking: Exakt > Prefix nach "mdi:" > Wort-Anfang > Substring
        exact   = [ic for ic in all_icons if ic == f"mdi:{q}"]
        prefix  = [ic for ic in all_icons if ic.startswith(f"mdi:{q}") and ic not in exact]
        word    = [ic for ic in all_icons if f"-{q}" in ic and ic not in exact and ic not in prefix]
        rest    = [ic for ic in all_icons if q in ic and ic not in exact and ic not in prefix and ic not in word]
        filtered = exact + prefix + word + rest
    else:
        # Ohne Suchbegriff: häufige Home-Remote-Icons zuerst
        priority = ["mdi:power","mdi:power-off","mdi:home","mdi:home-outline","mdi:menu",
                    "mdi:play","mdi:pause","mdi:stop","mdi:rewind","mdi:fast-forward",
                    "mdi:skip-previous","mdi:skip-next","mdi:record","mdi:record-rec",
                    "mdi:volume-plus","mdi:volume-minus","mdi:volume-mute","mdi:volume-high",
                    "mdi:arrow-up","mdi:arrow-down","mdi:arrow-left","mdi:arrow-right",
                    "mdi:chevron-up","mdi:chevron-down","mdi:chevron-left","mdi:chevron-right",
                    "mdi:circle","mdi:close","mdi:check","mdi:keyboard-return",
                    "mdi:netflix","mdi:youtube","mdi:spotify","mdi:television",
                    "mdi:bluetooth","mdi:radio","mdi:hdmi-port","mdi:video-input-hdmi",
                    "mdi:microphone","mdi:microphone-off","mdi:star","mdi:heart",
                    "mdi:information","mdi:cog","mdi:remote","mdi:remote-tv",
                    "mdi:gamepad","mdi:speaker","mdi:equalizer","mdi:fan",
                    "mdi:numeric-0","mdi:numeric-1","mdi:numeric-2","mdi:numeric-3",
                    "mdi:green","mdi:red","mdi:yellow","mdi:blue",
                    "mdi:square","mdi:triangle","mdi:circle-outline",
                    "mdi:sleep","mdi:timer","mdi:alarm","mdi:bell",
                    "mdi:apps","mdi:view-grid","mdi:format-list-bulleted",
                    "mdi:keyboard","mdi:backspace","mdi:delete",
                    "mdi:magnify","mdi:shuffle","mdi:repeat","mdi:repeat-once"]
        rest = [ic for ic in all_icons if ic not in priority]
        filtered = priority + rest
    return jsonify(filtered[:max_n])

@app.route("/api/ha-remotes")
def ha_remotes():
    """Remote-Entities aus HA (für Selectbox)."""
    env = _load_wizard_env()
    if not env:
        return jsonify({"error": "wizard.env nicht konfiguriert"}), 500
    try:
        import urllib.request
        req = urllib.request.Request(
            f"{env['HA_URL']}/api/states",
            headers={"Authorization": f"Bearer {env['HA_TOKEN']}"}
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            states = json.loads(r.read())
        remotes = sorted(s["entity_id"] for s in states
                         if s["entity_id"].startswith("remote."))
        return jsonify({"remotes": remotes})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/deploy", methods=["POST"])
def api_deploy():
    """Generierte Karte direkt in HA Lovelace deployen (WebSocket)."""
    data = request.json or {}
    room_id = data.get("room_id", "")
    card_path = os.path.join(CARDS, f"{room_id}.yaml")
    if not os.path.exists(card_path):
        return jsonify({"error": "Karte nicht generiert"}), 404

    env = _load_wizard_env()
    if not env:
        return jsonify({"error": "wizard.env nicht konfiguriert"}), 500

    try:
        import yaml as _yaml
        card_yaml = open(card_path, encoding="utf-8").read()
        new_views = _yaml.safe_load(
            "\n".join(l for l in card_yaml.splitlines() if not l.startswith("#"))
        ).get("views", [])
    except Exception as e:
        return jsonify({"error": f"YAML-Fehler: {e}"}), 500

    try:
        import websocket as _ws
        ws = _ws.create_connection(
            env["HA_URL"].replace("http://","ws://").replace("https://","wss://") + "/api/websocket",
            timeout=10
        )
        ws.recv()
        ws.send(json.dumps({"type": "auth", "access_token": env["HA_TOKEN"]}))
        auth_r = json.loads(ws.recv())
        if auth_r.get("type") != "auth_ok":
            return jsonify({"error": "HA Auth fehlgeschlagen"}), 500

        # Aktuelle Config laden
        ws.send(json.dumps({"id": 1, "type": "lovelace/config", "url_path": None}))
        cfg_r = json.loads(ws.recv())
        if not cfg_r.get("success"):
            return jsonify({"error": "Lovelace Config nicht lesbar"}), 500
        config = cfg_r["result"]

        # Views: eigene -gen Pfade ersetzen; fremde Pfade nie überschreiben
        existing = config.get("views", [])
        existing_paths = {v.get("path") for v in existing}
        new_paths = {nv.get("path") for nv in new_views}
        # Konflikt nur bei Pfaden, die NICHT mit -gen enden (Nutzerdaten)
        conflicts = [p for p in new_paths if p in existing_paths and not str(p).endswith("-gen")]
        if conflicts:
            ws.close()
            return jsonify({
                "error": f"Pfad-Konflikt: {conflicts} existiert bereits in Lovelace. "
                         f"Bitte zuerst die alte Seite umbenennen oder löschen.",
                "conflict_paths": conflicts
            }), 409
        # -gen Views ersetzen, alle anderen behalten
        config["views"] = [v for v in existing if v.get("path") not in new_paths] + new_views

        # Speichern
        ws.send(json.dumps({"id": 2, "type": "lovelace/config/save", "config": config}))
        save_r = json.loads(ws.recv())
        ws.close()

        if save_r.get("success"):
            return jsonify({"ok": True, "views_deployed": [v.get("path") for v in new_views]})
        else:
            return jsonify({"error": "Lovelace Save fehlgeschlagen", "detail": save_r}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/load-layout/<room_id>/<device_id>")
def api_load_layout(room_id, device_id):
    """Gespeichertes Editor-Layout (sections) für ein Gerät laden."""
    p = os.path.join(LOCAL, f"{room_id}.{device_id}.layout.json")
    if not os.path.exists(p):
        return jsonify({"error": "kein gespeichertes Layout"}), 404
    data = json.load(open(p, encoding="utf-8"))
    return jsonify({"sections": data.get("sections"), "saved": True})

@app.route("/api/save-layout", methods=["POST"])
def api_save_layout():
    """Layout (sections + rows + custom_actions) für ein Gerät speichern → Karte neu generieren."""
    data = request.json or {}
    room_id  = data.get("room_id", "")
    dev_id   = data.get("device_id", "")
    rows     = data.get("rows", [])
    actions  = data.get("custom_actions", [])
    if not room_id or not dev_id:
        return jsonify({"error": "room_id / device_id fehlt"}), 400

    layout_path = os.path.join(LOCAL, f"{room_id}.layout.json")
    layout = {}
    if os.path.exists(layout_path):
        layout = json.load(open(layout_path, encoding="utf-8"))
    layout[dev_id] = {"rows": rows, "custom_actions": actions}
    with open(layout_path, "w", encoding="utf-8") as f:
        json.dump(layout, f, indent=2, ensure_ascii=False)

    # Editor-State (sections) pro Gerät speichern — für späteres Laden/Bearbeiten
    sections = data.get("sections")
    if sections is not None:
        dev_layout_path = os.path.join(LOCAL, f"{room_id}.{dev_id}.layout.json")
        with open(dev_layout_path, "w", encoding="utf-8") as f:
            json.dump({"sections": sections, "device_id": dev_id, "room_id": room_id}, f, indent=2, ensure_ascii=False)

    # Karte neu generieren
    model_path = os.path.join(LOCAL, f"{room_id}.model.json")
    card_path  = os.path.join(CARDS, f"{room_id}.yaml")
    r = subprocess.run(
        [sys.executable, os.path.join(GEN, "build_cards.py"),
         "--model", model_path, "--out", card_path],
        capture_output=True, text=True, cwd=REPO
    )
    return jsonify({"ok": r.returncode == 0, "stdout": r.stdout.strip(), "stderr": r.stderr[:300]})

@app.route("/api/scenarios/<room_id>", methods=["GET"])
def get_scenarios(room_id):
    """Szenario-Konfiguration lesen (Labels + Icons)."""
    sce_path = os.path.join(LOCAL, f"{room_id}.scenarios.json")
    data = json.load(open(sce_path)) if os.path.exists(sce_path) else {}
    # Modell-Szenarien als Basis zurückgeben
    model_path = os.path.join(LOCAL, f"{room_id}.model.json")
    if not os.path.exists(model_path):
        return jsonify([])
    model = json.load(open(model_path))
    result = []
    for s in model.get("scenarios", []):
        sid = s["id"]
        override = data.get(sid, {})
        result.append({
            "id": sid,
            "name": s["name"],
            "label": override.get("label", ""),
            "icon":  override.get("icon",  ""),
        })
    return jsonify(result)

@app.route("/api/scenarios/<room_id>", methods=["POST"])
def save_scenarios(room_id):
    """Szenario-Konfiguration speichern und Karte neu bauen."""
    scenarios = request.json  # [{id, label, icon}, ...]
    sce_path = os.path.join(LOCAL, f"{room_id}.scenarios.json")
    os.makedirs(LOCAL, exist_ok=True)
    overrides = {s["id"]: {k: s[k] for k in ("label","icon") if s.get(k)} for s in scenarios}
    with open(sce_path, "w") as f:
        json.dump(overrides, f, indent=2, ensure_ascii=False)
    # Karte neu bauen
    model_path = os.path.join(LOCAL, f"{room_id}.model.json")
    card_path  = os.path.join(CARDS, f"{room_id}.yaml")
    r = subprocess.run(
        [sys.executable, os.path.join(GEN, "build_cards.py"),
         "--model", model_path, "--out", card_path],
        capture_output=True, text=True, cwd=REPO)
    return jsonify({"ok": r.returncode == 0, "stderr": r.stderr[:200]})


@app.route("/api/card-style/<room_id>", methods=["GET"])
def api_get_card_style(room_id):
    """Style-Konfiguration für einen Raum laden."""
    p = os.path.join(LOCAL, f"{room_id}.cardstyle.json")
    if not os.path.exists(p):
        # Default-Preset zurückgeben
        from build_cards import DEFAULT_STYLE
        return jsonify(DEFAULT_STYLE)
    return jsonify(json.load(open(p, encoding="utf-8")))

@app.route("/api/card-style/<room_id>", methods=["POST"])
def api_save_card_style(room_id):
    """Style-Konfiguration speichern."""
    data = request.json or {}
    p = os.path.join(LOCAL, f"{room_id}.cardstyle.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return jsonify({"ok": True})


def _load_wizard_env():
    path = os.path.join(LOCAL, "wizard.env")
    if not os.path.exists(path):
        return None
    env = {}
    for line in open(path):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env if "HA_URL" in env and "HA_TOKEN" in env else None

if __name__ == "__main__":
    print(f"Wizard läuft auf http://0.0.0.0:8777  (Repo: {REPO})")
    app.run(host="0.0.0.0", port=8777, debug=False)

