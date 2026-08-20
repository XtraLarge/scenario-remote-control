# Scenario Remote Control

[![HA App](https://img.shields.io/badge/Home%20Assistant-App-blue?logo=home-assistant)](https://www.home-assistant.io/addons/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Activity-based remote control cards for **Home Assistant** (Lovelace).  
Shows exactly the remote controls for the devices involved in the **current activity** —  
instead of static, hand-coded button panels.

> **Backend**: [Logitech Harmony](https://www.home-assistant.io/integrations/harmony/) (current reference).  
> Goal: make the backend **swappable** (Broadlink, ESPHome-IR, Unfolded Circle, SofaBaton, native HA) without changing models or cards.

---

## ✨ Features

- **Visual layout editor** — no YAML editing required
- Drag-and-drop buttons, circlepads, D-pads, volume controls, numpad, sliders
- 7000+ MDI icons per button
- Per-device accent colour + CSS presets (Glossy, Glass, Gradient, Flat, Minimal)
- Framed sections with labels
- Configurable hold / double-tap actions
- One-click **Lovelace deployment** via WebSocket
- Activity roster configuration with display names and icons
- Layout export/import (JSON)

Generated cards use [universal-remote-card](https://github.com/Nerwyn/universal-remote-card) (install via HACS).

---

## 🔧 Installation

### Prerequisites

1. **universal-remote-card** — install via HACS (Frontend → search "universal-remote-card")
2. Home Assistant OS or Supervised installation (required for Apps)

### Add the App repository

1. In Home Assistant: **Settings → Apps → App Store** (three-dot menu) → **Custom repositories**
2. Add: `https://github.com/XtraLarge/scenario-remote-control`  
   Category: **Apps**
3. Find **Scenario Remote Control** in the store → **Install**

### Open the Wizard

The wizard appears in the HA sidebar as **Remote Wizard** after installation.  
Alternatively: `http://<ha-host>:8777`

---

## 🚀 Quick start

1. **Source** — select your Harmony hub (`.conf` file from `/config/harmony_*.conf`)
2. **Wizard Step 1** — configure devices per room
3. **Editor** — arrange buttons, icons and sections visually
4. **Deploy** — push directly to your Lovelace dashboard

---

## 🏗 Architecture

```
Modell (/data)        Backend (/backends)       Präsentation (/cards)
Hub → Scenarios  →   Harmony / Broadlink /  →   universal-remote-card
→ Devices            ESPHome-IR / native         YAML (generated)
→ Commands
```

Three decoupled layers — swap the backend without touching models or cards.

---

## 📦 Repository structure

```
/
├── config.yaml          # HA App metadata
├── Dockerfile           # Multi-arch container build
├── run.sh               # App entry point
├── build.yaml           # HA Builder config
├── generator/
│   ├── build_cards.py   # Model → Lovelace YAML
│   ├── extract_harmony.py
│   └── wizard/          # Flask web wizard (port 8777)
│       ├── app.py
│       ├── templates/
│       └── static/
├── data/
│   ├── model.schema.json
│   └── example/         # Sanitised example (no personal data)
└── backends/
    └── harmony.yaml     # Reference backend config
```

> **Privacy**: real device names, hub IDs and activity names stay in `/data` (gitignored).  
> Only the toolkit and a sanitised example are in this repo.

---

## 🔄 Roadmap

- [x] P0 Scaffold
- [x] P1 Model + activity→device roster (Harmony, Wohnzimmer)
- [x] P2 Reference card (universal-remote-card, Harmony backend)
- [x] P3 Generator (all activities) + activity-driven card switching
- [ ] P4 Backend abstraction + one non-Harmony path (Broadlink / ESPHome-IR)
- [ ] P5 Rollout to multiple rooms, replace legacy HTML cards

---

## 📄 License

MIT — see [LICENSE](LICENSE).

[universal-remote-card]: https://github.com/Nerwyn/universal-remote-card
