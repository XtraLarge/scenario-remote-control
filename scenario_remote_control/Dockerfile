ARG BUILD_FROM
FROM ${BUILD_FROM}

WORKDIR /app
COPY generator/wizard/requirements.txt ./requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

COPY generator/ ./generator/

# s6-overlay v3 service definition
COPY rootfs/ /
RUN chmod a+x /etc/s6-overlay/s6-rc.d/scenario_remote_control/run
