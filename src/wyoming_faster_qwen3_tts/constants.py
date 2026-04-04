from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ModelProfile:
    model_name: str
    model_revision: str
    required_files: tuple[str, ...]
    expected_sha256: dict[str, str]
    prune_unused: bool = True

    @property
    def modelscope_url(self) -> str:
        return f"https://modelscope.cn/models/{self.model_name}"

SUPPORTED_LANGUAGES = [
    "zh",
    "en",
    "ja",
    "ko",
    "de",
    "fr",
    "ru",
    "pt",
    "es",
    "it",
]

SPEAKER_ORDER = [
    "Serena",
    "Vivian",
    "Uncle_Fu",
    "Dylan",
    "Eric",
    "Ryan",
    "Aiden",
    "Ono_Anna",
    "Sohee",
]

SPEAKER_METADATA = {
    "Vivian": {
        "languages": ["zh-CN"],
        "description": "明亮的年轻女声。",
    },
    "Serena": {
        "languages": ["zh-CN"],
        "description": "温暖柔和的年轻女声。",
    },
    "Uncle_Fu": {
        "languages": ["zh-CN"],
        "description": "成熟男声，音色醇厚。",
    },
    "Dylan": {
        "languages": ["zh-CN"],
        "description": "充满青春气息的北京男声。",
    },
    "Eric": {
        "languages": ["zh-CN"],
        "description": "活泼的成都男声。",
    },
    "Ryan": {
        "languages": ["en"],
        "description": "富有节奏感的活力男声。",
    },
    "Aiden": {
        "languages": ["en"],
        "description": "阳光的美式男声。",
    },
    "Ono_Anna": {
        "languages": ["ja"],
        "description": "活泼的日语女声。",
    },
    "Sohee": {
        "languages": ["ko"],
        "description": "温暖的韩语女声。",
    },
}

_COMMON_REQUIRED_FILES = (
    "model.safetensors",
    "config.json",
    "configuration.json",
    "generation_config.json",
    "preprocessor_config.json",
    "tokenizer_config.json",
    "vocab.json",
    "merges.txt",
    "speech_tokenizer/config.json",
    "speech_tokenizer/configuration.json",
    "speech_tokenizer/preprocessor_config.json",
    "speech_tokenizer/model.safetensors",
)

_EXPECTED_SHA256_0_6B = {
    "model.safetensors": "bc3c7e785eb961179c25450d1acff03f839e0002f2f3a5aeb67b5735c0fa2adb",
    "speech_tokenizer/model.safetensors": "836b7b357f5ea43e889936a3709af68dfe3751881acefe4ecf0dbd30ba571258",
}

_MODEL_0_6B_ID = "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"
_MODEL_1_7B_ID = "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"

MODEL_PROFILES: dict[str, ModelProfile] = {
    _MODEL_0_6B_ID: ModelProfile(
        model_name=_MODEL_0_6B_ID,
        model_revision="master",
        required_files=_COMMON_REQUIRED_FILES,
        expected_sha256=_EXPECTED_SHA256_0_6B,
    ),
    _MODEL_1_7B_ID: ModelProfile(
        model_name=_MODEL_1_7B_ID,
        model_revision="master",
        required_files=_COMMON_REQUIRED_FILES,
        expected_sha256={},
    ),
}

DEFAULT_MODEL_NAME = _MODEL_0_6B_ID
DEFAULT_MODEL_REVISION = MODEL_PROFILES[DEFAULT_MODEL_NAME].model_revision


def modelscope_url_for_model(model_name: str) -> str:
    return f"https://modelscope.cn/models/{model_name}"


def model_profile_for_name(model_name: str) -> ModelProfile | None:
    return MODEL_PROFILES.get(model_name)


def default_model_dir(project_root: Path, model_name: str = DEFAULT_MODEL_NAME) -> Path:
    return project_root / "data" / "models" / model_name.replace("/", "__")
