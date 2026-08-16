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
    confs = list_confs()
    return render_template("step1.html", conf_files=confs)

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
    """MDI-Icon-Suche (aus eingebetteter Icon-Liste)."""
    q = request.args.get("q", "").lower()
    # Häufige Icons für Fernbedienungen
    icons = [
        "mdi:power","mdi:power-on","mdi:power-off","mdi:power-standby",
        "mdi:home","mdi:home-outline","mdi:home-circle",
        "mdi:menu","mdi:apps","mdi:dots-horizontal","mdi:dots-grid",
        "mdi:arrow-up","mdi:arrow-down","mdi:arrow-left","mdi:arrow-right",
        "mdi:chevron-up","mdi:chevron-down","mdi:chevron-left","mdi:chevron-right",
        "mdi:circle","mdi:checkbox-marked-circle","mdi:check-circle",
        "mdi:arrow-left-circle","mdi:close-circle","mdi:close",
        "mdi:play","mdi:pause","mdi:stop","mdi:record","mdi:record-rec",
        "mdi:rewind","mdi:fast-forward","mdi:skip-previous","mdi:skip-next",
        "mdi:volume-plus","mdi:volume-minus","mdi:volume-mute","mdi:volume-high",
        "mdi:television","mdi:television-guide","mdi:television-play","mdi:television-classic",
        "mdi:satellite-uplink","mdi:satellite","mdi:antenna",
        "mdi:microphone","mdi:microphone-outline","mdi:voice",
        "mdi:netflix","mdi:youtube","mdi:spotify","mdi:music",
        "mdi:bluetooth","mdi:bluetooth-audio","mdi:bluetooth-connect",
        "mdi:radio","mdi:radio-tower",
        "mdi:hdmi-port","mdi:video-input-hdmi","mdi:video-input-component",
        "mdi:sony-playstation","mdi:microsoft-xbox","mdi:nintendo-switch",
        "mdi:subtitles","mdi:subtitles-outline","mdi:text",
        "mdi:information","mdi:information-outline",
        "mdi:cog","mdi:cog-outline","mdi:tune","mdi:tune-variant",
        "mdi:sleep","mdi:sleep-off","mdi:timer",
        "mdi:lightbulb","mdi:lightbulb-outline",
        "mdi:star","mdi:star-outline","mdi:heart","mdi:bookmark",
        "mdi:format-list-bulleted","mdi:view-grid","mdi:view-list",
        "mdi:swap-horizontal","mdi:shuffle","mdi:repeat",
        "mdi:numeric-0","mdi:numeric-1","mdi:numeric-2","mdi:numeric-3",
        "mdi:numeric-4","mdi:numeric-5","mdi:numeric-6","mdi:numeric-7",
        "mdi:numeric-8","mdi:numeric-9",
        "mdi:gamepad","mdi:gamepad-variant","mdi:controller-classic",
        "mdi:fan","mdi:fan-off","mdi:air-conditioner","mdi:weather-windy",
        "mdi:speaker","mdi:speaker-wireless","mdi:speaker-multiple",
        "mdi:equalizer","mdi:waveform","mdi:surround-sound",
        "mdi:skip-backward","mdi:skip-forward","mdi:step-backward","mdi:step-forward",
        "mdi:keyboard","mdi:keyboard-return","mdi:keyboard-backspace",
        "mdi:delete","mdi:delete-outline","mdi:backspace","mdi:backspace-outline",
        "mdi:magnify","mdi:magnify-plus","mdi:magnify-minus",
        "mdi:lock","mdi:lock-open","mdi:key",
        "mdi:bell","mdi:bell-outline","mdi:bell-off",
        "mdi:wifi","mdi:lan","mdi:web","mdi:server",
        "mdi:usb","mdi:usb-port",
        "mdi:input","mdi:output","mdi:import","mdi:export",
        "mdi:page-next","mdi:page-previous","mdi:book-open",
        "mdi:image","mdi:camera","mdi:video","mdi:movie-open",
        "mdi:green","mdi:red","mdi:yellow","mdi:blue",
        "mdi:square","mdi:circle-outline","mdi:triangle",
        "mdi:ab-testing","mdi:remote","mdi:remote-tv",
    ]
    if q:
        filtered = [i for i in icons if q in i.lower()]
    else:
        filtered = icons
    return jsonify(filtered[:60])

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

        # Views: neue ersetzen / anhängen
        existing = config.get("views", [])
        for nv in new_views:
            path = nv.get("path")
            existing = [v for v in existing if v.get("path") != path]
            existing.append(nv)
        config["views"] = existing

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

@app.route("/api/save-layout", methods=["POST"])
def api_save_layout():
    """Layout (rows + custom_actions) für ein Gerät speichern → Karte neu generieren."""
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

    # Karte neu generieren
    model_path = os.path.join(LOCAL, f"{room_id}.model.json")
    card_path  = os.path.join(CARDS, f"{room_id}.yaml")
    r = subprocess.run(
        [sys.executable, os.path.join(GEN, "build_cards.py"),
         "--model", model_path, "--out", card_path,
         "--layout", layout_path],
        capture_output=True, text=True, cwd=REPO
    )
    return jsonify({"ok": r.returncode == 0, "stdout": r.stdout.strip(), "stderr": r.stderr[:300]})

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

