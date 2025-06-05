FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    apt-utils \
    build-essential \
    curl \
    automake \
    autoconf \
    libtool \
    wget \
    libpmi2-0-dev \
    ca-certificates \
    software-properties-common \
    gnupg \
    curl \
    lsb-release \
    pciutils \
    tesseract-ocr \
    && apt-get clean && rm -rf /var/lib/apt/lists/* && update-ca-certificates --fresh

ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
ENV SSL_CERT_DIR=/etc/ssl/certs

RUN python3.11 -m pip install --upgrade pip setuptools wheel

RUN python3.11 -m pip install playwright
RUN python3.11 -m playwright install-deps