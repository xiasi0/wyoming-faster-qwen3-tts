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
        "Service ready uri=%s model_dir=%s default_language=%s default_speaker=%s chunk_size=%d",
        settings.uri,
        settings.model_dir,
        settings.default_language,
        settings.default_speaker,
        settings.chunk_size,
    )
    state = AppState(settings=settings, model_service=model_service)
    server = AsyncServer.from_uri(settings.uri)
    await server.run(lambda reader, writer: FasterQwen3TtsEventHandler(reader, writer, state=state))


def main() -> None:
    asyncio.run(amain())


if __name__ == "__main__":
    main()
