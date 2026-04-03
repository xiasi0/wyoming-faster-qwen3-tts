#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -eq 0 ] || [ "${1#-}" != "$1" ]; then
  set -- wyoming-faster-qwen3-tts "$@"
fi

if [ "$1" = "wyoming-faster-qwen3-tts" ]; then
  echo "Starting wyoming-faster-qwen3-tts with env:"
  echo "  language=${language:-${tts_language:-${TTS_LANGUAGE:-Chinese}}}"
  echo "  speaker=${speaker:-${tts_speaker:-${TTS_SPEAKER:-Serena}}}"
  echo "  log_level=${log_level:-${tts_log_level:-${TTS_LOG_LEVEL:-INFO}}}"
  if [ -n "${instruct:-${tts_instruct:-${WQ3TTS_INSTRUCT:-}}}" ]; then
    echo "  instruct=set"
  else
    echo "  instruct=unset"
  fi
fi

exec "$@"
