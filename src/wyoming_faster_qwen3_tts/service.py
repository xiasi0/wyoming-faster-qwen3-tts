from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from threading import Lock
from typing import Iterator

import torch
from faster_qwen3_tts import FasterQwen3TTS

from .cleanup import cleanup_project_junk
from .config import Settings
from .constants import SPEAKER_ORDER
from .downloader import ensure_model_downloaded, verify_model_directory

_LOGGER = logging.getLogger(__name__)

_DTYPE_MAP = {
    "bf16": torch.bfloat16,
    "fp16": torch.float16,
    "fp32": torch.float32,
}

_SPEAKER_ORDER_MAP = {speaker.lower(): index for index, speaker in enumerate(SPEAKER_ORDER)}


@dataclass(frozen=True)
class SynthesisRequest:
    text: str
    speaker: str
    language: str
    instruct: str | None = None


class ModelService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._load_lock = Lock()
        self._infer_lock = Lock()
        self._model: FasterQwen3TTS | None = None
        self._supported_speakers: list[str] = []
        self._speaker_lookup: dict[str, str] = {}

    def startup(self) -> None:
        cleanup_project_junk(self.settings.project_root, self.settings.model_dir)
        model_dir = ensure_model_downloaded(self.settings.model_dir)
        verify_model_directory(model_dir)
        self._get_model()
        self._warmup()

    @property
    def supported_speakers(self) -> list[str]:
        self._get_model()
        return list(self._supported_speakers)

    def default_speaker(self) -> str:
        speakers = self.supported_speakers
        if self.settings.default_speaker:
            default = self.resolve_speaker(self.settings.default_speaker)
            if default is None:
                raise ValueError(f"Configured default speaker is not available: {self.settings.default_speaker}")
            return default
        if not speakers:
            raise ValueError("The model did not report any supported speakers")
        return speakers[0]

    def resolve_speaker(self, requested_speaker: str) -> str | None:
        self._get_model()
        return self._speaker_lookup.get(requested_speaker.lower())

    def synthesize_streaming(self, request: SynthesisRequest) -> Iterator[tuple]:
        with self._infer_lock:
            model = self._get_model()
            start_time = time.perf_counter()
            chunk_count = 0
            sample_rate = None
            total_samples = 0
            try:
                for chunk_count, item in enumerate(
                    model.generate_custom_voice_streaming(
                        text=request.text,
                        speaker=request.speaker,
                        language=request.language,
                        instruct=request.instruct,
                        chunk_size=self.settings.chunk_size,
                    ),
                    start=1,
                ):
                    audio_chunk, sample_rate, timing = item
                    total_samples += len(audio_chunk)
                    yield item
            finally:
                elapsed_s = time.perf_counter() - start_time
                audio_duration_s = 0.0
                if sample_rate:
                    audio_duration_s = total_samples / sample_rate
                _LOGGER.info(
                    "Synthesis finished speaker=%s language=%s chars=%d chunks=%d audio_s=%.2f elapsed_s=%.2f rtf=%.2f",
                    request.speaker,
                    request.language,
                    len(request.text),
                    chunk_count,
                    audio_duration_s,
                    elapsed_s,
                    (audio_duration_s / elapsed_s) if elapsed_s > 0 else 0.0,
                )

    def _get_model(self) -> FasterQwen3TTS:
        with self._load_lock:
            if self._model is not None:
                return self._model

            _LOGGER.info("Loading faster-qwen3-tts model from %s", self.settings.model_dir)
            self._model = FasterQwen3TTS.from_pretrained(
                str(self.settings.model_dir),
                device=self.settings.device,
                dtype=_DTYPE_MAP[self.settings.dtype],
                attn_implementation="sdpa",
                max_seq_len=2048,
            )
            speakers = self._model.model.get_supported_speakers() or []
            self._supported_speakers = sorted(
                speakers,
                key=lambda speaker: (
                    _SPEAKER_ORDER_MAP.get(speaker.lower(), len(_SPEAKER_ORDER_MAP)),
                    speaker.lower(),
                ),
            )
            self._speaker_lookup = {speaker.lower(): speaker for speaker in self._supported_speakers}
            _LOGGER.info("Model ready with %d speakers", len(self._supported_speakers))
            return self._model

    def _warmup(self) -> None:
        speaker = self.default_speaker()
        warmup_text = "你好。"
        start_time = time.perf_counter()
        chunks = 0
        for chunks, _item in enumerate(
            self.synthesize_streaming(
                SynthesisRequest(
                    text=warmup_text,
                    speaker=speaker,
                    language=self.settings.default_language,
                    instruct=self.settings.instruct,
                )
            ),
            start=1,
        ):
            pass
        _LOGGER.info(
            "Warmup complete speaker=%s instruct=%s elapsed_s=%.2f",
            speaker,
            "set" if self.settings.instruct else "unset",
            time.perf_counter() - start_time,
        )
