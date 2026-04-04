from __future__ import annotations

import logging
import time
from contextlib import suppress
from dataclasses import dataclass
from threading import Lock
from typing import Iterator

import torch
from faster_qwen3_tts import FasterQwen3TTS

from .cleanup import cleanup_project_junk
from .config import Settings
from .constants import SPEAKER_ORDER, SUPPORTED_LANGUAGES, model_profile_for_name
from .downloader import ensure_model_downloaded, verify_model_directory

_LOGGER = logging.getLogger(__name__)

_DTYPE_MAP = {
    "bf16": torch.bfloat16,
    "fp16": torch.float16,
    "fp32": torch.float32,
}

_SPEAKER_ORDER_MAP = {speaker.lower(): index for index, speaker in enumerate(SPEAKER_ORDER)}
_LANGUAGE_MAP = {
    "zh": "Chinese",
    "zh-cn": "Chinese",
    "zh-hans": "Chinese",
    "en": "English",
    "en-us": "English",
    "ja": "Japanese",
    "ja-jp": "Japanese",
    "ko": "Korean",
    "ko-kr": "Korean",
    "de": "German",
    "de-de": "German",
    "fr": "French",
    "fr-fr": "French",
    "ru": "Russian",
    "ru-ru": "Russian",
    "pt": "Portuguese",
    "pt-br": "Portuguese",
    "pt-pt": "Portuguese",
    "es": "Spanish",
    "es-es": "Spanish",
    "it": "Italian",
    "it-it": "Italian",
    "auto": "Auto",
}

_MODEL_LANGUAGE_TO_TAG = {
    "chinese": "zh-CN",
    "english": "en-US",
    "japanese": "ja-JP",
    "korean": "ko-KR",
    "german": "de-DE",
    "french": "fr-FR",
    "russian": "ru-RU",
    "portuguese": "pt-BR",
    "spanish": "es-ES",
    "italian": "it-IT",
}


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
        self._supported_languages: list[str] = list(SUPPORTED_LANGUAGES)
        self._speaker_lookup: dict[str, str] = {}

    def startup(self) -> None:
        cleanup_project_junk(self.settings.project_root, self.settings.model_dir)
        model_profile = model_profile_for_name(self.settings.model_name)
        if model_profile is None:
            raise ValueError(
                f"Unsupported model_name: {self.settings.model_name}. "
                "Supported models: Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice, "
                "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"
            )
        if not model_profile.expected_sha256:
            _LOGGER.warning(
                "Model %s has no pinned SHA256 verification in this project; only required-file checks will be used.",
                self.settings.model_name,
            )
        model_dir = ensure_model_downloaded(self.settings.model_dir, model_profile)
        verify_model_directory(model_dir, model_profile.required_files, model_profile.expected_sha256)
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

    @property
    def supported_languages(self) -> list[str]:
        self._get_model()
        return list(self._supported_languages)

    def resolve_speaker(self, requested_speaker: str) -> str | None:
        self._get_model()
        return self._speaker_lookup.get(requested_speaker.lower())

    def normalize_language(self, language: str) -> str:
        return _LANGUAGE_MAP.get(language.strip().lower(), language)

    def synthesize_streaming(self, request: SynthesisRequest) -> Iterator[tuple]:
        with self._infer_lock:
            model = self._get_model()
            start_time = time.perf_counter()
            chunk_count = 0
            sample_rate = None
            total_samples = 0
            first_chunk_elapsed_s: float | None = None
            first_prefill_ms: float | None = None
            try:
                for chunk_count, item in enumerate(
                    model.generate_custom_voice_streaming(
                        text=request.text,
                        speaker=request.speaker,
                        language=self.normalize_language(request.language),
                        instruct=request.instruct,
                        non_streaming_mode=self.settings.non_streaming_mode,
                        max_new_tokens=self.settings.max_new_tokens,
                        min_new_tokens=self.settings.min_new_tokens,
                        temperature=self.settings.temperature,
                        top_k=self.settings.top_k,
                        top_p=self.settings.top_p,
                        do_sample=self.settings.do_sample,
                        repetition_penalty=self.settings.repetition_penalty,
                        chunk_size=self.settings.chunk_size,
                    ),
                    start=1,
                ):
                    audio_chunk, sample_rate, timing = item
                    if first_chunk_elapsed_s is None:
                        first_chunk_elapsed_s = time.perf_counter() - start_time
                        if isinstance(timing, dict):
                            first_prefill_ms = timing.get("prefill_ms")
                        _LOGGER.info(
                            "Model first chunk speaker=%s language=%s chars=%d first_chunk_s=%.3f prefill_ms=%s",
                            request.speaker,
                            request.language,
                            len(request.text),
                            first_chunk_elapsed_s,
                            f"{first_prefill_ms:.1f}" if isinstance(first_prefill_ms, (int, float)) else "n/a",
                        )
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
            raw_languages = None
            with suppress(Exception):
                if hasattr(self._model.model, "get_supported_languages"):
                    raw_languages = self._model.model.get_supported_languages()  # type: ignore[attr-defined]
            if raw_languages:
                mapped_languages: list[str] = []
                for language in raw_languages:
                    key = str(language).strip().lower()
                    mapped_languages.append(_MODEL_LANGUAGE_TO_TAG.get(key, str(language)))
                self._supported_languages = sorted({lang for lang in mapped_languages if lang})
            else:
                self._supported_languages = list(SUPPORTED_LANGUAGES)
            _LOGGER.info("Model ready with %d speakers", len(self._supported_speakers))
            return self._model

    def _warmup(self) -> None:
        speaker = self.default_speaker()
        warmup_text = "你好。"
        start_time = time.perf_counter()
        for _item in self.synthesize_streaming(
            SynthesisRequest(
                text=warmup_text,
                speaker=speaker,
                language=self.normalize_language(self.settings.default_language),
                instruct=self.settings.instruct,
            )
        ):
            pass
        _LOGGER.info(
            "Warmup complete speaker=%s instruct=%s elapsed_s=%.2f",
            speaker,
            "set" if self.settings.instruct else "unset",
            time.perf_counter() - start_time,
        )
