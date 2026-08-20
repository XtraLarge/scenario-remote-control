#!/usr/bin/env bashio
# Scenario Remote Control — HA App entry point

LOG_LEVEL=$(bashio::config 'log_level' 'info')
bashio::log.info "Starting Scenario Remote Control Wizard ..."

# Paths
export DATA_DIR="/data"
export CONF_DIR="/homeassistant"         # HA config dir (harmony .conf files)
export GEN_DIR="/app/generator"
export CARDS_DIR="/data/cards"

# Create data dirs if missing
mkdir -p "${DATA_DIR}" "${CARDS_DIR}"

# Port from Ingress
PORT=$(bashio::addon.ingress_port)
bashio::log.info "Listening on port ${PORT} (Ingress)"

exec python3 /app/generator/wizard/app.py --port "${PORT}"
