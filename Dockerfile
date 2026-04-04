FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PYTHONPATH=/app/src

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        sox \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /app/
COPY src /app/src

RUN if python3 -m pip install --help 2>/dev/null | grep -q -- "--break-system-packages"; then \
        PIP_SYSTEM="--break-system-packages"; \
    else \
        PIP_SYSTEM=""; \
    fi \
    && python3 -m pip install ${PIP_SYSTEM} --upgrade pip setuptools wheel \
    && python3 -m pip install ${PIP_SYSTEM} /app \
    && python3 -c "import wyoming, numpy, modelscope, faster_qwen3_tts, wyoming_faster_qwen3_tts" \
    && (python3 -m pip cache purge >/dev/null 2>&1 || true) \
    && rm -rf /root/.cache /tmp/*

EXPOSE 10200

VOLUME ["/app/data"]

CMD ["python3", "-m", "wyoming_faster_qwen3_tts"]
