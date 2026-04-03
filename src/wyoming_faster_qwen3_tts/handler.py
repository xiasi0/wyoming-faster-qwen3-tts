from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from dataclasses import dataclass

from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.info import Attribution, Describe, Info, TtsProgram, TtsVoice
from wyoming.server import AsyncEventHandler
from wyoming.tts import Synthesize, SynthesizeChunk, SynthesizeStart, SynthesizeStop, SynthesizeStopped, SynthesizeVoice

from .audio import float32_to_pcm16_bytes, pcm16_millis
from .config import Settings
from .constants import MODELSCOPE_MODEL_URL, SPEAKER_METADATA, SUPPORTED_LANGUAGES
from .service import ModelService, SynthesisRequest

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class AppState:
    settings: Settings
    model_service: ModelService


class FasterQwen3TtsEventHandler(AsyncEventHandler):
    def __init__(self, *args, state: AppState, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.state = state
        self.client_name = self._describe_peer()
        self._stream_voice: SynthesizeVoice | None = None
        self._stream_chunks: list[str] = []
        self._stream_full_text: str | None = None
        _LOGGER.info("Client connected: %s", self.client_name)

    async def handle_event(self, event) -> bool:
        _LOGGER.debug("Received Wyoming event type=%s from %s", event.type, self.client_name)
        if Describe.is_type(event.type):
            await self.write_event(self._info_event().event())
            return True

        if SynthesizeStart.is_type(event.type):
            stream_start = SynthesizeStart.from_event(event)
            self._stream_voice = stream_start.voice
            self._stream_chunks = []
            self._stream_full_text = None
            _LOGGER.debug("Synthesize streaming started client=%s", self.client_name)
            return True

        if SynthesizeChunk.is_type(event.type):
            stream_chunk = SynthesizeChunk.from_event(event)
            self._stream_chunks.append(stream_chunk.text)
            _LOGGER.debug(
                "Received synthesize chunk client=%s chunk_chars=%d total_chunks=%d",
                self.client_name,
                len(stream_chunk.text),
                len(self._stream_chunks),
            )
            return True

        if Synthesize.is_type(event.type):
            synthesize = Synthesize.from_event(event)
            if self._stream_voice is not None or self._stream_chunks:
                self._stream_full_text = synthesize.text
                if synthesize.voice is not None:
                    self._stream_voice = synthesize.voice
                _LOGGER.debug(
                    "Received compatibility synthesize event for streaming request client=%s text_chars=%d",
                    self.client_name,
                    len(synthesize.text),
                )
                return True
            await self._handle_synthesize(synthesize)
            return True

        if SynthesizeStop.is_type(event.type):
            text = self._stream_full_text if self._stream_full_text is not None else "".join(self._stream_chunks)
            voice = self._stream_voice
            self._stream_voice = None
            self._stream_chunks = []
            self._stream_full_text = None
            synthesize = Synthesize(text=text, voice=voice)
            _LOGGER.info(
                "Synthesize request client=%s chars=%d",
                self.client_name,
                len(text),
            )
            await self._handle_synthesize(synthesize)
            await self.write_event(SynthesizeStopped().event())
            _LOGGER.debug("Sent synthesize-stopped client=%s", self.client_name)
            return True

        _LOGGER.warning("Ignoring unsupported Wyoming event: %s", event.type)
        return True

    async def disconnect(self) -> None:
        _LOGGER.info("Client disconnected: %s", self.client_name)
        with suppress(Exception):
            await self.writer.wait_closed()

    def _info_event(self) -> Info:
        program = TtsProgram(
            name="wyoming-faster-qwen3-tts",
            attribution=Attribution(name="Qwen", url=MODELSCOPE_MODEL_URL),
            installed=True,
            description="Wyoming TTS service backed by faster-qwen3-tts",
            version=None,
            voices=self._voices(),
            supports_synthesize_streaming=True,
        )
        return Info(tts=[program])

    def _voices(self) -> list[TtsVoice]:
        voices: list[TtsVoice] = []
        for speaker in self.state.model_service.supported_speakers:
            metadata = SPEAKER_METADATA.get(
                speaker,
                {"languages": SUPPORTED_LANGUAGES, "description": f"{speaker} speaker"},
            )
            voices.append(
                TtsVoice(
                    name=speaker,
                    attribution=Attribution(name="Qwen", url=MODELSCOPE_MODEL_URL),
                    installed=True,
                    description=metadata["description"],
                    version=None,
                    languages=metadata["languages"],
                    speakers=None,
                )
            )
        return voices

    async def _handle_synthesize(self, synthesize: Synthesize) -> None:
        speaker = self._resolve_speaker(synthesize)
        language = self._resolve_language(synthesize)
        _LOGGER.info("Synthesize request client=%s speaker=%s language=%s chars=%d", self.client_name, speaker, language, len(synthesize.text))
        request = SynthesisRequest(
            text=synthesize.text,
            speaker=speaker,
            language=language,
            instruct=self.state.settings.instruct,
        )

        queue: asyncio.Queue[object] = asyncio.Queue()
        loop = asyncio.get_running_loop()
        done = object()
        worker_error: list[BaseException] = []

        def run_synthesis() -> None:
            try:
                for audio_chunk, sample_rate, _timing in self.state.model_service.synthesize_streaming(request):
                    payload = float32_to_pcm16_bytes(audio_chunk)
                    if payload:
                        loop.call_soon_threadsafe(queue.put_nowait, (sample_rate, payload))
            except BaseException as err:  # propagate worker failures back into the handler
                worker_error.append(err)
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, done)

        worker_task = asyncio.create_task(asyncio.to_thread(run_synthesis))
        sample_rate = None
        timestamp_ms = 0
        started = False

        while True:
            item = await queue.get()
            if item is done:
                break

            sample_rate, payload = item
            _LOGGER.debug(
                "Streaming audio chunk client=%s speaker=%s bytes=%d timestamp_ms=%d",
                self.client_name,
                speaker,
                len(payload),
                timestamp_ms,
            )
            if not started:
                await self.write_event(
                    AudioStart(rate=sample_rate, width=2, channels=1, timestamp=timestamp_ms).event()
                )
                _LOGGER.debug("Audio stream started client=%s speaker=%s sample_rate=%s", self.client_name, speaker, sample_rate)
                started = True
            await self.write_event(
                AudioChunk(
                    rate=sample_rate,
                    width=2,
                    channels=1,
                    audio=payload,
                    timestamp=timestamp_ms,
                ).event()
            )
            timestamp_ms += pcm16_millis(payload, sample_rate, channels=1)

        await worker_task
        if worker_error:
            raise worker_error[0]

        if sample_rate is None:
            raise RuntimeError("Synthesis produced no audio")

        if not started:
            await self.write_event(AudioStart(rate=sample_rate, width=2, channels=1, timestamp=0).event())

        await self.write_event(AudioStop(timestamp=timestamp_ms).event())
        _LOGGER.debug("Audio stream stopped client=%s speaker=%s total_ms=%d", self.client_name, speaker, timestamp_ms)

    def _resolve_speaker(self, synthesize: Synthesize) -> str:
        requested_speaker = None
        if synthesize.voice is not None:
            if synthesize.voice.speaker:
                requested_speaker = synthesize.voice.speaker
            elif synthesize.voice.name:
                requested_speaker = synthesize.voice.name
        if not requested_speaker:
            return self.state.model_service.default_speaker()

        speaker = self.state.model_service.resolve_speaker(requested_speaker)
        if speaker is not None:
            return speaker

        raise ValueError(f"Unknown speaker requested: {requested_speaker}")

    def _resolve_language(self, synthesize: Synthesize) -> str:
        if synthesize.voice and synthesize.voice.language:
            return self.state.model_service.normalize_language(synthesize.voice.language)
        return self.state.model_service.normalize_language(self.state.settings.default_language)

    def _describe_peer(self) -> str:
        with suppress(Exception):
            peer = self.writer.get_extra_info("peername")
            if peer:
                return str(peer)
        return "unknown"
