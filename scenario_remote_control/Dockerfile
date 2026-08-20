ARG BUILD_FROM
FROM ${BUILD_FROM}

WORKDIR /app
COPY generator/wizard/requirements.txt ./requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

COPY generator/ ./generator/
COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD ["/run.sh"]
