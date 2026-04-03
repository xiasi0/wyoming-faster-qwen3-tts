from __future__ import annotations

import numpy as np


def float32_to_pcm16_bytes(audio: np.ndarray) -> bytes:
    pcm = np.asarray(audio, dtype=np.float32).reshape(-1)
    pcm = np.clip(pcm, -1.0, 1.0)
    return (pcm * 32767.0).astype(np.int16).tobytes()


def pcm16_millis(payload: bytes, sample_rate: int, channels: int = 1) -> int:
    sample_width = 2
    samples = len(payload) // (sample_width * channels)
    return int(samples / sample_rate * 1000)
