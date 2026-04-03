#!/usr/bin/env bash
set -euo pipefail

bootstrap_python_deps() {
  if python3 -c "import wyoming, numpy, modelscope, faster_qwen3_tts" >/dev/null 2>&1; then
    return
  fi

  echo "Installing Python dependencies inside container..."
  python3 -m pip install --break-system-packages --upgrade pip setuptools wheel
  python3 -m pip install --break-system-packages \
    faster-qwen3-tts \
    modelscope \
    numpy \
    wyoming
  python3 -c "import wyoming, numpy, modelscope, faster_qwen3_tts"
  python3 -m pip cache purge >/dev/null 2>&1 || true
  rm -rf /root/.cache/pip /tmp/*
}

if [ "$#" -eq 0 ] || [ "${1#-}" != "$1" ]; then
  set -- python3 -m wyoming_faster_qwen3_tts "$@"
fi

if [ "$1" = "python3" ] && [ "${2:-}" = "-m" ] && [ "${3:-}" = "wyoming_faster_qwen3_tts" ]; then
  echo "Starting wyoming-faster-qwen3-tts with env:"
  echo "  language=${language:-${tts_language:-${TTS_LANGUAGE:-Chinese}}}"
  echo "  speaker=${speaker:-${tts_speaker:-${TTS_SPEAKER:-Serena}}}"
  echo "  log_level=${log_level:-${tts_log_level:-${TTS_LOG_LEVEL:-INFO}}}"
  if [ -n "${instruct:-${tts_instruct:-${WQ3TTS_INSTRUCT:-}}}" ]; then
    echo "  instruct=set"
  else
    echo "  instruct=unset"
  fi
  bootstrap_python_deps
fi

exec "$@"
