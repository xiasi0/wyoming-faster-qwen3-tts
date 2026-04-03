# wyoming-faster-qwen3-tts

Wyoming TTS service for Home Assistant backed by `faster-qwen3-tts`.

## Upstream Projects

- `wyoming`: https://github.com/OHF-Voice/wyoming
- `faster-qwen3-tts`: https://github.com/andimarafioti/faster-qwen3-tts
- `Qwen3-TTS-12Hz-0.6B-CustomVoice` on ModelScope: https://modelscope.cn/models/Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice

## Scope

This first version is intentionally narrow:

- `CustomVoice` only
- `Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice` only
- automatic ModelScope download into `data/models`
- startup fails fast if download, checksum validation, or local model loading fails
- standard Wyoming `synthesize` input
- streamed PCM audio output for faster response

## Run

```bash
python -m pip install -e .
wyoming-faster-qwen3-tts
```

## Docker

Build the image:

```bash
docker build -t wyoming-faster-qwen3-tts .
```

Run with NVIDIA GPU support and persist downloaded models under `${HOME}/data/models`:

```bash
docker run --rm \
  --gpus all \
  -p 10200:10200 \
  -v "${HOME}/data/models:/app/data/models" \
  wyoming-faster-qwen3-tts
```

Run with a fixed instruction prompt:

```bash
docker run --rm \
  --gpus all \
  -p 10200:10200 \
  -v "${HOME}/data/models:/app/data/models" \
  -e instruct="用温柔自然的语气说" \
  wyoming-faster-qwen3-tts
```

Notes:

- The container requires the NVIDIA Container Toolkit on the host.
- The first container start downloads the model into `/app/data/models`, mapped from `${HOME}/data/models` on the host.
- The `sox` package is installed in the image to avoid the startup warning from upstream dependencies.
- The container logs show both application logs and ModelScope download progress on stdout/stderr.
- The Compose file declares the application runtime defaults explicitly: `language=zh-CN`, `speaker=serena`, `log_level=info`, and a default `instruct`.

Use Docker Compose:

```bash
docker compose up --build
```

The included [docker-compose.yml](/root/wyoming-faster-qwen3-tts/docker-compose.yml) maps:

- `10200:10200`
- `${HOME}/data/models:/app/data/models`

If you want to add a fixed instruction prompt in Compose, add this under the service:

```yaml
environment:
  instruct: 用温柔自然的语气说
```

Optional container environment variables:

- `language`
- `speaker`
- `log_level`
- `instruct`

## Notes

- CUDA is required because `faster-qwen3-tts` does not support CPU inference.
- On first start, the service downloads the model from ModelScope into `data/models`.
- The service verifies expected SHA-256 checksums for the two large safetensor files before loading.
