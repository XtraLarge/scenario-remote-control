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

## Offener Punkt P1
Die `harmony_*.conf` liefert Activities (id→Label) und Devices (→commands), aber **nicht**
das Szenario→Geräte-Roster. Dieses wird in P1 ermittelt (aus der bestehenden FB-Karte oder
dem Hub) und ins Modell überführt.

## Backend-Kandidaten für die Ablösung
harmony (jetzt) · broadlink/esphome-ir · unfolded-circle · sofabaton · native.
Umschaltung erfolgt allein über die Backend-Auswahl des jeweiligen Hubs im Modell.
