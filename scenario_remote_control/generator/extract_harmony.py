#!/usr/bin/env python3
"""extract_harmony.py — harmony_*.conf + Roster-Map -> Modell (data/local/*.model.json).

Die .conf liefert Activities (id->Name) und Devices (Name->commands+id), aber NICHT
das Szenario->Geraete-Roster. Dieses (plus Anzeige-ids/-namen) kommt aus einer
Roster-Map (home-spezifisch, gehoert nach data/local/, gitignored). So bleibt dieses
Skript generisch/committbar und personenbezogene Daten bleiben lokal.

Map-Format (JSON):
{
  "hub":     {"id":"wz","name":"<Raum>","backend":"harmony","entity":"remote.<raum>_hub"},
  "devices": {"<harmony device name>": {"id":"tv","name":"<Anzeigename>"}, ...},
  "scenarios":{"<harmony activity name>": {"id":"<szenario-id>","name":"<Anzeige>",
               "primaryDevice":"<device-id>","devices":["<device-id>", ...]}, ...}
}
Nicht in der Map gelistete Activities (z.B. PowerOff) werden uebersprungen.
Roster-Herleitung fuer Harmony/HA: aus den FB-Karten-Bedingungen (z.B.
binary_sensor.*_show_card_* in template.yaml) ablesen, welche Geraete-FB je Activity
eingeblendet werden.
"""
import argparse, json, sys

def build(conf, m):
    dmap = m["devices"]
    devices = []
    for hname, info in conf["Devices"].items():
        if hname not in dmap:
            continue
        d = dmap[hname]
        devices.append({
            "id": d["id"], "name": d["name"],
            "backend": {"harmony": {"device": hname, "device_id": info.get("id")}},
            "commands": [{"id": c} for c in info["commands"]],
        })
    smap = m["scenarios"]
    scenarios = []
    for aname in conf["Activities"].values():
        if aname not in smap:
            continue
        s = smap[aname]
        scenarios.append({
            "id": s["id"], "name": s["name"], "hub": m["hub"]["id"],
            "backend": {"harmony": {"activity": aname}},
            "primaryDevice": s.get("primaryDevice"),
            "devices": s["devices"],
        })
    return {"hubs": [m["hub"]], "devices": devices, "scenarios": scenarios}

def validate(model, schema=None):
    errs = []
    dev_ids = {d["id"] for d in model["devices"]}
    hub_ids = {h["id"] for h in model["hubs"]}
    for s in model["scenarios"]:
        if s["hub"] not in hub_ids: errs.append(f"{s['id']}: hub {s['hub']} unbekannt")
        pd = s.get("primaryDevice")
        if pd and pd not in dev_ids: errs.append(f"{s['id']}: primaryDevice {pd} nicht in devices")
        if pd and pd not in s["devices"]: errs.append(f"{s['id']}: primaryDevice {pd} nicht im Roster")
        for d in s["devices"]:
            if d not in dev_ids: errs.append(f"{s['id']}: roster-device {d} unbekannt")
    for d in model["devices"]:
        if not d.get("commands"): errs.append(f"device {d['id']}: keine commands")
    if schema is not None:
        try:
            import jsonschema
            jsonschema.validate(model, schema)
        except ImportError:
            print("[warn] jsonschema nicht installiert — nur Referenz-Checks", file=sys.stderr)
    return errs

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--conf", required=True)
    ap.add_argument("--map", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--schema", default="data/model.schema.json")
    a = ap.parse_args()
    conf = json.load(open(a.conf))
    m = json.load(open(a.map))
    model = build(conf, m)
    schema = None
    try: schema = json.load(open(a.schema))
    except OSError: pass
    errs = validate(model, schema)
    if errs:
        print("VALIDIERUNG FEHLGESCHLAGEN:", file=sys.stderr)
        for e in errs: print("  !", e, file=sys.stderr)
        sys.exit(1)
    json.dump(model, open(a.out, "w"), indent=2, ensure_ascii=False)
    print(f"OK: {a.out} — {len(model['devices'])} devices, {len(model['scenarios'])} scenarios")

if __name__ == "__main__":
    main()
