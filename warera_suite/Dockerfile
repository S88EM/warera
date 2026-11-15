ARG BUILD_FROM=ghcr.io/home-assistant/base:latest
FROM ${BUILD_FROM}

ENV LANG=C.UTF-8
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install Python 3, pip and tools via apk
RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-setuptools \
    py3-wheel \
    curl \
    jq

# Install dependencies with break-system-packages for Alpine 3.19+
COPY requirements.txt /app/
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

# Copy all application code
COPY . /app/
RUN chmod +x /app/run.sh

CMD [ "/app/run.sh" ]
