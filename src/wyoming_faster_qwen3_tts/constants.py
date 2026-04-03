from pathlib import Path

MODEL_ID = "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"
MODEL_REVISION = "master"
MODELSCOPE_MODEL_URL = "https://modelscope.cn/models/Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"

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

EXPECTED_SHA256 = {
    "model.safetensors": "bc3c7e785eb961179c25450d1acff03f839e0002f2f3a5aeb67b5735c0fa2adb",
    "speech_tokenizer/model.safetensors": "836b7b357f5ea43e889936a3709af68dfe3751881acefe4ecf0dbd30ba571258",
}

REQUIRED_FILES = tuple(EXPECTED_SHA256.keys()) + (
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
)


def default_model_dir(project_root: Path) -> Path:
    return project_root / "data" / "models" / "Qwen__Qwen3-TTS-12Hz-0.6B-CustomVoice"
