ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base-python:3.12-alpine3.18
FROM ${BUILD_FROM}

# HA Add-on paths (Supervisor mounts /data automatically; harmony conf uploaded via UI)
ENV DATA_DIR=/data \
    GEN_DIR=/app/generator \
    CARDS_DIR=/data/cards

WORKDIR /app
COPY generator/wizard/requirements.txt ./requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

COPY generator/ ./generator/

# Flask as PID 1 (bypass s6-overlay — not compatible with HA Supervisor 2026.07 for unsigned apps)
ENTRYPOINT ["python3", "/app/generator/wizard/app.py", "--port", "8777"]
