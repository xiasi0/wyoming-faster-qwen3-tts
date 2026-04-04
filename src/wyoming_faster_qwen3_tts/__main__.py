from __future__ import annotations

import asyncio
import logging

from wyoming.server import AsyncServer

from .config import parse_args
from .handler import AppState, FasterQwen3TtsEventHandler
from .service import ModelService


async def amain() -> None:
    settings = parse_args()
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger = logging.getLogger(__name__)

    model_service = ModelService(settings)
    await asyncio.to_thread(model_service.startup)
    logger.info(
        "Service ready uri=%s model_name=%s revision=%s model_dir=%s default_language=%s default_speaker=%s non_streaming_mode=%s chunk_size=%d temperature=%.2f top_k=%d top_p=%.2f do_sample=%s repetition_penalty=%.2f max_new_tokens=%d min_new_tokens=%d instruct=%s",
        settings.uri,
        settings.model_name,
        settings.model_revision,
        settings.model_dir,
        settings.default_language,
        settings.default_speaker,
        settings.non_streaming_mode,
        settings.chunk_size,
        settings.temperature,
        settings.top_k,
        settings.top_p,
        settings.do_sample,
        settings.repetition_penalty,
        settings.max_new_tokens,
        settings.min_new_tokens,
        "set" if settings.instruct else "unset",
    )
    state = AppState(settings=settings, model_service=model_service)
    server = AsyncServer.from_uri(settings.uri)
    await server.run(lambda reader, writer: FasterQwen3TtsEventHandler(reader, writer, state=state))


def main() -> None:
    asyncio.run(amain())


if __name__ == "__main__":
    main()
