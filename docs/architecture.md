# Architektur & Harmony-Ablöseplan

## Warum 3 Schichten
Das abgekündigte Harmony-System soll mittel-/langfristig herauslösbar sein. Deshalb hängt
weder das Modell noch die Karte an Harmony — nur ein austauschbares **Backend**.

```
[ Modell /data ]  ->  [ Generator ]  ->  [ Karten /cards (universal-remote-card) ]
        |                                        |
        +-----------> [ Backend /backends ] <----+   (Aktion ausführen)
```

## Szenario-Konzept
Ein **Szenario** (= Harmony-Activity) referenziert die **beteiligten Geräte** (Roster).
Ist ein Szenario aktiv, zeigt die Oberfläche genau diese Geräte-Fernbedienungen.

## P1 — Modell + Roster (erledigt)
Die `harmony_*.conf` liefert Activities (id→Label) und Devices (→commands), aber **nicht**
das Szenario→Geräte-Roster. In P1 gelöst:

- **Modell-Erweiterung:** `devices` und `scenarios` tragen ein `backend`-Binding
  (z. B. `{"harmony": {"device": "…"}}` bzw. `{"harmony": {"activity": "…"}}`).
  So bleibt der Anzeigename backend-unabhängig; ein Backend-Wechsel ändert nur das Binding.
- **Roster-Herleitung:** Welche Geräte-FB je Activity eingeblendet werden, steht in den
  Bedingungen der bestehenden FB-Karte (HA `binary_sensor.<raum>_show_card_*` in
  `template.yaml`). Genau diese Zuordnung wird als `scenario.devices` (Roster) übernommen.
- **Generator:** `generator/extract_harmony.py` erzeugt aus `harmony_*.conf` + einer
  home-spezifischen Roster-Map (`data/local/*.map.json`, gitignored) das validierte Modell
  (`data/local/*.model.json`). So ist das Modell reproduzierbar statt handgepflegt.
- **WZ** ist als erster Raum vollständig erfasst: 5 Geräte, 6 Szenarien mit Roster.

## Backend-Kandidaten für die Ablösung
harmony (jetzt) · broadlink/esphome-ir · unfolded-circle · sofabaton · native.
Umschaltung erfolgt allein über die Backend-Auswahl des jeweiligen Hubs im Modell.
