# /generator

- `extract_harmony.py` — `harmony_*.conf` + Roster-Map → validiertes Modell (`data/local/*.model.json`). **[P1 implementiert]**
  Geräte/Commands kommen aus der `.conf`; das Szenario→Geräte-**Roster** und Anzeige-ids/-namen
  liefert eine home-spezifische Map (`data/local/*.map.json`, gitignored). Roster-Quelle: die
  Bedingungen der bestehenden FB-Karte (`binary_sensor.<raum>_show_card_*` in `template.yaml`).
  Aufruf: `python3 generator/extract_harmony.py --conf … --map … --out …`
- `build_cards.py` — Modell + gewähltes Backend → universal-remote-card YAML (`/cards`).

`build_cards.py` ist noch nicht implementiert (P3).
