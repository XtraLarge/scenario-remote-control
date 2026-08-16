# /generator

- `extract_harmony.py` — `harmony_*.conf` → Modell (`data/local/model.json`).
  Ermittelt Szenario→Geräte-**Roster** (Quelle: aktuelle FB-Karte bzw. Harmony-Hub — wird in P1 festgelegt).
- `build_cards.py` — Modell + gewähltes Backend → universal-remote-card YAML (`/cards`).

Noch nicht implementiert (P1/P3). Dieses Verzeichnis enthält vorerst die Spezifikation.
