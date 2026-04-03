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

### 1) 拉取代码并进入目录

```bash
git clone https://github.com/xiasi0/wyoming-faster-qwen3-tts.git
cd wyoming-faster-qwen3-tts
```

### 2) 推荐：使用 Docker Compose 启动

```bash
docker compose up -d --build
```

查看日志：

```bash
docker compose logs -f
```

停止：

```bash
docker compose down
```

默认配置见 [docker-compose.yml](/root/wyoming-faster-qwen3-tts/docker-compose.yml)，包括：

- `10200:10200`
- `${HOME}/data/models:/app/data/models`
- `language=zh-CN`
- `speaker=serena`
- `log_level=info`
- `instruct`

### 3) 可选：本地运行（非 Docker）

```bash
python -m pip install -e .
wyoming-faster-qwen3-tts
```

本地默认值：

- `language=zh-CN`
- `speaker=serena`
- `log_level=info`
- `instruct` 默认不设置

常用参数：

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `--uri` | `tcp://0.0.0.0:10200` | Wyoming 服务监听地址 |
| `--device` | `cuda` | 推理设备，仅支持 CUDA |
| `--dtype` | `bf16` | 推理精度：`bf16`、`fp16`、`fp32` |
| `--default-language` | `zh-CN` | 默认语言 |
| `--default-speaker` | `Serena` | 默认 speaker |
| `--instruct` | 未设置 | 固定 instruction |
| `--chunk-size` | `8` | 流式输出 chunk 大小 |
| `--log-level` | `INFO` | 日志级别 |
| `--model-dir` | `data/models/Qwen__Qwen3-TTS-12Hz-0.6B-CustomVoice` | 模型目录 |

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
- 镜像构建阶段只安装系统包；Python 依赖会在容器启动时自动安装，然后再启动服务。
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
