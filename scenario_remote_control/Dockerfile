ARG BUILD_FROM
FROM ${BUILD_FROM}

# Install system dependencies
RUN apk add --no-cache python3 py3-pip

# Copy requirements first (layer cache)
WORKDIR /app
COPY generator/wizard/requirements.txt ./requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

# Copy application code
COPY generator/ ./generator/

# Entry point
COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD ["/run.sh"]
