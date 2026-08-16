# scenario-remote-control

Szenario-/aktionsbasierte Fernbedienungs-Oberfläche für **Home Assistant** (Lovelace).
Blendet auf Basis einer **Aktion/Activity** (an der mehrere Geräte beteiligt sind) genau die
Fernbedienungen der **beteiligten Geräte** ein — statt starrer, handgeklöppelter Buttons.

> Erstes Backend & erste Datenquelle: **Logitech Harmony** (abgekündigt). Ziel ist es,
> Harmony **austauschbar/wählbar** zu machen (IR-Blaster, Unfolded Circle, SofaBaton, native
> Integrationen) — ohne Modell oder Karten anzufassen.

## Architektur — 3 entkoppelte Schichten
1. **Modell** (`/data`) — Single Source of Truth (Harmony-unabhängig): Hubs → Szenarien →
   *beteiligte Geräte* → Commands. Siehe `data/model.schema.json` + `data/example/`.
2. **Backend** (`/backends`) — austauschbare Abbildung „Gerät+Command → HA-Aktion".
   Referenz: `harmony`. Kandidaten: `broadlink`/`esphome-ir`, `unfolded-circle`, `sofabaton`, `native`.
3. **Präsentation** (`/cards`) — aus dem Modell **generierte** [universal-remote-card]-Configs,
   szenario-gesteuert ein-/ausgeblendet.

## Generator (`/generator`)
- `harmony → model`: liest `harmony_*.conf` (Activities/Devices) + ermittelt das Szenario→Geräte-Roster.
- `model → cards`: erzeugt universal-remote-card YAML pro Szenario/Raum.

## Status / Roadmap (PDCA)
- [x] P0 Scaffold (dieses Repo)
- [ ] P1 Modell aus Harmony extrahieren (inkl. Szenario→Geräte-Roster) + verifizieren
- [ ] P2 Referenz-Karte (Wohnzimmer, eine Activity) mit universal-remote-card, Backend=harmony
- [ ] P3 Generator (alle Szenarien) + szenario-gesteuerte Einblendung
- [ ] P4 Backend-Abstraktion + ein Nicht-Harmony-Pfad exemplarisch
- [ ] P5 Rollout WZ/GZ/GH, alte HTML-Karten ablösen

## Datenschutz
Echte Activities/Geräte bleiben **lokal** in der HA-Config. Dieses Repo enthält nur das
**Toolkit + ein sanitisiertes Beispiel**.

[universal-remote-card]: https://github.com/Nerwyn/universal-remote-card
