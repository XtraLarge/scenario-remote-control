# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-08-20

### Added
- **Visual Layout Editor** — drag-and-drop canvas for building remote control layouts
  - Widget types: Button, Spacer, Circlepad, D-Pad, Numpad, Volume, Touchpad, Slider, Stack
  - Per-button properties: command, label, icon (7000+ MDI icons), hold/double-tap actions
  - Framed sections with custom titles
  - Per-device accent colour
  - CSS presets: Glossy (dark), Gradient, Flat, Glass, Minimal
- **Lovelace deployment** via WebSocket API (no YAML editing required)
- **Configurable Lovelace target** (view path + dashboard)
- **Layout export/import** (JSON)
- **Activity roster** configuration (step 2) with display name + icon per activity
- **Home Assistant App** packaging (Ingress, multi-arch, HA Supervisor)
- Harmony backend: reads `harmony_*.conf` from HA config directory
- Generated cards use [universal-remote-card](https://github.com/Nerwyn/universal-remote-card)

[Unreleased]: https://github.com/XtraLarge/scenario-remote-control/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/XtraLarge/scenario-remote-control/releases/tag/v0.1.0
