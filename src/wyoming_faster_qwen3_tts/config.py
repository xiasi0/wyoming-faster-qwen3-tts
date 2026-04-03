from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path

from .constants import MODEL_ID, default_model_dir


def _env(names: str | tuple[str, ...], default: str | None = None) -> str | None:
    if isinstance(names, str):
        names = (names,)
    for name in names:
        value = os.environ.get(name)
        if value is not None and value != "":
            return value
    return default


@dataclass(frozen=True)
class Settings:
    uri: str
    project_root: Path
    model_id: str
    model_dir: Path
    device: str
    dtype: str
    default_language: str
    default_speaker: str | None
    instruct: str | None
    chunk_size: int
    log_level: str


def parse_args() -> Settings:
    project_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(prog="wyoming-faster-qwen3-tts")
    parser.add_argument("--uri", default="tcp://0.0.0.0:10200", help="Wyoming server URI")
    parser.add_argument("--device", default="cuda", help="Torch device, must be CUDA")
    parser.add_argument("--dtype", default="bf16", choices=["bf16", "fp16", "fp32"])
    parser.add_argument(
        "--default-language",
        default=_env("language", "zh-CN"),
        help="Fallback language",
    )
    parser.add_argument(
        "--default-speaker",
        default=_env("speaker", "Serena"),
        help="Fallback speaker if none is requested",
    )
    parser.add_argument(
        "--instruct",
        default=_env("instruct"),
        help="Optional fixed instruction prompt for CustomVoice",
    )
    parser.add_argument("--chunk-size", type=int, default=8, help="Streaming chunk size for generated audio")
    parser.add_argument(
        "--log-level",
        default=_env("log_level", "INFO"),
        help="Python log level",
    )
    parser.add_argument(
        "--model-dir",
        default=str(default_model_dir(project_root)),
        help="Directory where the ModelScope snapshot should live",
    )
    args = parser.parse_args()
    return Settings(
        uri=args.uri,
        project_root=project_root,
        model_id=MODEL_ID,
        model_dir=Path(args.model_dir).resolve(),
        device=args.device,
        dtype=args.dtype,
        default_language=args.default_language,
        default_speaker=args.default_speaker,
        instruct=args.instruct,
        chunk_size=args.chunk_size,
        log_level=args.log_level.upper(),
    )
