# /generator

- `extract_harmony.py` — `harmony_*.conf` + Roster-Map → validiertes Modell (`data/local/*.model.json`). **[P1 implementiert]**
  Geräte/Commands kommen aus der `.conf`; das Szenario→Geräte-**Roster** und Anzeige-ids/-namen
  liefert eine home-spezifische Map (`data/local/*.map.json`, gitignored). Roster-Quelle: die
  Bedingungen der bestehenden FB-Karte (`binary_sensor.<raum>_show_card_*` in `template.yaml`).
  Aufruf: `python3 generator/extract_harmony.py --conf … --map … --out …`

- `build_cards.py` — validiertes Modell → Lovelace-YAML (`cards/local/*.yaml`). **[P2 implementiert]**
  Erzeugt eine HA-Lovelace-View mit Szenarien-Buttons (Harmony-Activity starten/stoppen)
  und Geräte-Fernbedienungen (grid, 4 Spalten) aus allen Commands des Modells.
  P2: Geräte-Cards statisch (alle sichtbar) — conditional Einblendung per aktivem Szenario kommt P3.
  Aufruf: `python3 generator/build_cards.py --model data/local/wz.model.json --out cards/local/wz.yaml`
  Sanitisiertes Beispiel: `cards/example/wz.example.yaml`
