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

if __name__ == "__main__":
    print(f"Wizard läuft auf http://0.0.0.0:8777  (Repo: {REPO})")
    app.run(host="0.0.0.0", port=8777, debug=False)
