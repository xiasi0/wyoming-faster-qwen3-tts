FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-venv \
        sox \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /app/
COPY src /app/src
COPY docker-entrypoint.sh /app/docker-entrypoint.sh

RUN python3 -m pip install --break-system-packages --upgrade pip setuptools wheel \
    && python3 -m pip install --break-system-packages . \
    && chmod +x /app/docker-entrypoint.sh \
    && python3 -m pip cache purge || true \
    && rm -rf /root/.cache /tmp/*

EXPOSE 10200

VOLUME ["/app/data"]

ENTRYPOINT ["/app/docker-entrypoint.sh"]

CMD []
