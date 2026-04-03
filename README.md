# wyoming-faster-qwen3-tts

基于 `faster-qwen3-tts` 的 Home Assistant Wyoming TTS 服务。

## 简介

当前第一版有意保持收敛，仅支持：

- `CustomVoice`
- `Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice`
- 启动时自动从 ModelScope 下载模型到 `data/models`
- 如果下载失败、校验失败或本地模型加载失败，服务会直接启动失败
- 输入使用标准 Wyoming `synthesize`
- 输出使用流式 PCM 音频，以获得更快响应

## 快速开始

### 本地运行

```bash
python -m pip install -e .
wyoming-faster-qwen3-tts
```

默认行为：

- `language=zh-CN`
- `speaker=serena`
- `log_level=info`
- 本地直接运行时默认不启用 `instruct`

本地运行参数：

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `--uri` | `tcp://0.0.0.0:10200` | Wyoming 服务监听地址 |
| `--device` | `cuda` | 推理设备，当前仅支持 CUDA |
| `--dtype` | `bf16` | 推理精度，可选 `bf16`、`fp16`、`fp32` |
| `--default-language` | `zh-CN` | 默认语言，对外使用语言标识符，内部会映射到上游支持的语言名 |
| `--default-speaker` | `Serena` | 默认 speaker |
| `--instruct` | 未设置 | 可选的固定 instruction，会作用于预热和后续请求 |
| `--chunk-size` | `8` | 流式音频输出的 chunk 大小 |
| `--log-level` | `INFO` | 日志级别 |
| `--model-dir` | `data/models/Qwen__Qwen3-TTS-12Hz-0.6B-CustomVoice` | 本地模型目录 |

### Docker

构建镜像：

```bash
docker build -t wyoming-faster-qwen3-tts .
```

运行容器：

```bash
docker run --rm \
  --gpus all \
  -p 10200:10200 \
  -v "${HOME}/data/models:/app/data/models" \
  wyoming-faster-qwen3-tts
```

带固定 instruction 运行：

```bash
docker run --rm \
  --gpus all \
  -p 10200:10200 \
  -v "${HOME}/data/models:/app/data/models" \
  -e instruct="用温柔自然的语气说" \
  wyoming-faster-qwen3-tts
```

### Docker Compose

启动：

```bash
docker compose up --build
```

当前 [docker-compose.yml](/root/wyoming-faster-qwen3-tts/docker-compose.yml) 默认包含：

- `10200:10200`
- `${HOME}/data/models:/app/data/models`
- `language=zh-CN`
- `speaker=serena`
- `log_level=info`
- 一条默认 `instruct`

如果你想调整固定 instruction，可以修改：

```yaml
environment:
  instruct: 用温柔自然的语气说
```

`docker-compose.yml` 环境变量：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `language` | `zh-CN` | 默认语言 |
| `speaker` | `serena` | 默认 speaker，大小写不敏感 |
| `log_level` | `info` | 日志级别，程序内部会自动转成大写使用 |
| `instruct` | `用自然、清晰、亲切的语气说` | Compose 默认固定 instruction |

## 运行说明

- 容器运行依赖宿主机已安装 NVIDIA Container Toolkit。
- 必须使用 CUDA，因为 `faster-qwen3-tts` 不支持纯 CPU 推理。
- 容器首次启动时会把模型下载到 `/app/data/models`，该目录映射到宿主机 `${HOME}/data/models`。
- 服务在加载前会校验两个大尺寸 `safetensors` 文件的 SHA-256。
- 镜像内已安装 `sox`，用于避免上游依赖启动时的相关告警。
- 容器日志会同时输出应用日志和 ModelScope 下载进度。

## 可选环境变量

- `language`
- `speaker`
- `log_level`
- `instruct`

## 引用项目

- `wyoming`: https://github.com/OHF-Voice/wyoming
- `faster-qwen3-tts`: https://github.com/andimarafioti/faster-qwen3-tts
- ModelScope 上的 `Qwen3-TTS-12Hz-0.6B-CustomVoice`:
  https://modelscope.cn/models/Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice
