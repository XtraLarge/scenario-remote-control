# /backends — austauschbare Steuer-Backends

Ein Backend bildet zwei Operationen auf HA-Aktionen ab:
- `startScenario(hub, scenario)` — startet eine Szene/Activity
- `sendCommand(hub, device, command)` — sendet einen Geräte-Command

So bleibt Modell + Karte identisch, egal ob Harmony, IR-Blaster, Unfolded Circle, SofaBaton
oder native Integrationen die Aktion tatsächlich ausführen.

| Backend | Status | startScenario | sendCommand |
|---|---|---|---|
| harmony | Referenz | remote.turn_on {activity} | remote.send_command {device,command} |
| broadlink / esphome-ir | geplant | scene/script | remote.send_command / esphome ir |
| unfolded-circle | geplant | UC activity | UC command |
| sofabaton | Kandidat | tbd | tbd |
| native | geplant | script je Gerät | native service je Gerät |
