# /cards

Generierte Lovelace-Karten (YAML) für Home Assistant. **NICHT manuell editieren** —
aus `data/local/*.model.json` via `generator/build_cards.py` erzeugt.

## Struktur

- `cards/local/` — generierte Karten mit echten Daten (gitignored)
- `cards/example/` — sanitisiertes Beispiel ohne Personendaten (committbar)

## Karte deployen

Die generierten YAML-Karten können als neue Lovelace-View in HA eingefügt werden
(via YAML-Modus oder WebSocket-API). Deploy-Automatisierung kommt in P3/P5.

## Generieren

```bash
python3 generator/build_cards.py \
  --model data/local/wz.model.json \
  --out   cards/local/wz.yaml
```
