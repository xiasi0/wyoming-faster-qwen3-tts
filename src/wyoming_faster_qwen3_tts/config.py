from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path

from .constants import (
    DEFAULT_MODEL_NAME,
    DEFAULT_MODEL_REVISION,
    default_model_dir,
    model_profile_for_name,
    modelscope_url_for_model,
)


def _env(names: str | tuple[str, ...], default: str | None = None) -> str | None:
    if isinstance(names, str):
        names = (names,)
    for name in names:
        value = os.environ.get(name)
        if value is not None and value != "":
            return value
    return default


def _env_bool(names: str | tuple[str, ...], default: bool = False) -> bool:
    value = _env(names)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    uri: str
    project_root: Path
    model_name: str
    model_revision: str
    model_url: str
    model_dir: Path
    device: str
    dtype: str
    default_language: str
    default_speaker: str | None
    instruct: str | None
    max_new_tokens: int
    min_new_tokens: int
    temperature: float
    top_k: int
    top_p: float
    do_sample: bool
    repetition_penalty: float
    non_streaming_mode: bool
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
    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=int(_env("max_new_tokens", "2048")),
        help="Maximum generated codec tokens",
    )
    parser.add_argument(
        "--min-new-tokens",
        type=int,
        default=int(_env("min_new_tokens", "2")),
        help="Minimum generated codec tokens",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=float(_env("temperature", "0.9")),
        help="Sampling temperature",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=int(_env("top_k", "50")),
        help="Top-k sampling",
    )
    parser.add_argument(
        "--top-p",
        type=float,
        default=float(_env("top_p", "1.0")),
        help="Top-p sampling",
    )
    parser.add_argument(
        "--do-sample",
        action=argparse.BooleanOptionalAction,
        default=_env_bool("do_sample", True),
        help="Enable sampling (disable for deterministic decoding)",
    )
    parser.add_argument(
        "--repetition-penalty",
        type=float,
        default=float(_env("repetition_penalty", "1.05")),
        help="Repetition penalty",
    )
    parser.add_argument(
        "--non-streaming-mode",
        action=argparse.BooleanOptionalAction,
        default=_env_bool("non_streaming_mode", False),
        help="Use full-text prefill mode in upstream runtime (higher first-audio latency)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=int(_env("chunk_size", "4")),
        help="Streaming chunk size for generated audio (smaller = earlier first audio chunk)",
    )
    parser.add_argument(
        "--log-level",
        default=_env("log_level", "INFO"),
        help="Python log level",
    )
    parser.add_argument(
        "--model-name",
        default=_env(("model_name", "MODEL_NAME"), DEFAULT_MODEL_NAME),
        help="ModelScope model name (e.g. Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice)",
    )
    parser.add_argument(
        "--model-dir",
        default=_env(("model_dir", "MODEL_DIR")),
        help="Directory where the ModelScope snapshot should live",
    )
    args = parser.parse_args()
    model_name = args.model_name.strip()

    model_profile = model_profile_for_name(model_name)
    model_revision = model_profile.model_revision if model_profile is not None else DEFAULT_MODEL_REVISION
    model_dir = Path(args.model_dir).resolve() if args.model_dir else default_model_dir(project_root, model_name)
    return Settings(
        uri=args.uri,
        project_root=project_root,
        model_name=model_name,
        model_revision=model_revision,
        model_url=modelscope_url_for_model(model_name),
        model_dir=model_dir,
        device=args.device,
        dtype=args.dtype,
        default_language=args.default_language,
        default_speaker=args.default_speaker,
        instruct=args.instruct,
        max_new_tokens=args.max_new_tokens,
        min_new_tokens=args.min_new_tokens,
        temperature=args.temperature,
        top_k=args.top_k,
        top_p=args.top_p,
        do_sample=args.do_sample,
        repetition_penalty=args.repetition_penalty,
        non_streaming_mode=args.non_streaming_mode,
        chunk_size=args.chunk_size,
        log_level=args.log_level.upper(),
    )
