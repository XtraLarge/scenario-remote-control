ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base-python:3.12-alpine3.18
FROM ${BUILD_FROM}

# HA Add-on fixed paths (mounted by Supervisor)
ENV DATA_DIR=/data \
    CONF_DIR=/homeassistant \
    GEN_DIR=/app/generator \
    CARDS_DIR=/data/cards

WORKDIR /app
COPY generator/wizard/requirements.txt ./requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

COPY generator/ ./generator/

# Bypass s6-overlay — run Flask directly as PID 1
ENTRYPOINT ["python3", "/app/generator/wizard/app.py", "--port", "8777"]
