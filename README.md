# wyoming-faster-qwen3-tts

基于 `faster-qwen3-tts` 的 Home Assistant Wyoming TTS 服务。

## 简介

当前第一版有意保持收敛，仅支持：

- `CustomVoice`
- `Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice`
- `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice`
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
docker compose build
docker compose up -d
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
- `model_name=Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice`
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
| `--instruct` | 未设置 | 设了会更有“语气风格”，不设更中性 |
| `--max-new-tokens` | `2048` | 调大可说更长，太大可能更慢 |
| `--min-new-tokens` | `2` | 调大可减少过短输出，太大可能拖长尾音 |
| `--temperature` | `0.9` | 调大更有变化，调小更稳更一致 |
| `--top-k` | `50` | 调小更稳，调大更灵活 |
| `--top-p` | `1.0` | 调小更稳，调大更自由 |
| `--do-sample` | `true` | `false` 更稳定，`true` 更自然有变化 |
| `--repetition-penalty` | `1.05` | 调大可减少重复，太大会不自然 |
| `--chunk-size` | `4` | 调小首包更快，调大更省开销但首包更慢 |
| `--log-level` | `INFO` | 日志级别 |
| `--model-name` | `Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice` | ModelScope 模型名称 |
| `--model-dir` | `data/models/<model_name 替换 / 为 __>` | 模型目录 |

`docker-compose.yml` 环境变量：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `model_name` | `Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice` | 模型名称，可切到 1.7B |
| `language` | `zh-CN` | 默认语言 |
| `speaker` | `serena` | 默认 speaker，大小写不敏感 |
| `log_level` | `info` | 日志级别，程序内部会自动转成大写使用 |
| `instruct` | `用自然、清晰、亲切的语气说` | 设了更有风格，不设更中性 |
| `chunk_size` | `4` | 调小首包更快，调大更省开销但首包更慢 |
| `non_streaming_mode` | `false` | `false` 首包快，`true` 通常更慢 |
| `temperature` | `0.9` | 调大更有变化，调小更稳 |

说明：示例 YAML 仅放了少量高价值参数；其余参数请按需自行追加到 `environment`。

快速建议：

- 想更快开口：优先保持 `non_streaming_mode=false`，并适当减小 `chunk_size`。
- 想更稳定一致：适当降低 `temperature`，并可把 `do_sample` 设为 `false`。
- 想更有风格：设置 `instruct`，例如“温和、简洁、慢一点”。

## 运行说明

- 容器运行依赖宿主机已安装 NVIDIA Container Toolkit。
- 必须使用 CUDA，因为 `faster-qwen3-tts` 不支持纯 CPU 推理。
- 容器首次启动时会把模型下载到 `/app/data/models`，该目录映射到宿主机 `${HOME}/data/models`。
- Python 依赖已经固化在镜像构建阶段，容器每次启动不会再执行 `pip install`。
- 0.6B 模型会校验两个大尺寸 `safetensors` 文件的 SHA-256。
- 1.7B 模型当前执行“必需文件存在性校验”，不做固定 SHA-256 校验。
- 镜像内已安装 `sox`，用于避免上游依赖启动时的相关告警。
- 容器日志会同时输出应用日志和 ModelScope 下载进度。

## 可选环境变量

- `language`
- `speaker`
- `log_level`
- `instruct`
- `max_new_tokens`
- `min_new_tokens`
- `temperature`
- `top_k`
- `top_p`
- `do_sample`
- `repetition_penalty`
- `non_streaming_mode`
- `chunk_size`
- `model_name`
- `model_dir`

## 切换到 1.7B 示例

默认使用 0.6B。切到 1.7B 直接改 `docker-compose.yml` 中的 `model_name`：

```yaml
environment:
  model_name: Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice
```

应用配置：

```bash
docker compose up -d --no-build
```

## 配置与更新建议

- 修改 `docker-compose.yml` 的 `environment` 配置后，执行：

```bash
docker compose up -d --no-build
```

- 这会更新容器配置，但不会重新构建镜像，也不会重新安装 Python 依赖。
- 模型切换直接修改 `model_name` 后执行 `docker compose up -d --no-build`。
- 只有代码或依赖变化时，才需要执行 `docker compose build`。

切回 0.6B 只需把 `model_name` 改回：

```yaml
environment:
  model_name: Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice
```

## 引用项目

- `wyoming`: https://github.com/OHF-Voice/wyoming
- `faster-qwen3-tts`: https://github.com/andimarafioti/faster-qwen3-tts
- ModelScope 上的 `Qwen3-TTS-12Hz-0.6B-CustomVoice`:
  https://modelscope.cn/models/Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice
- ModelScope 上的 `Qwen3-TTS-12Hz-1.7B-CustomVoice`:
  https://modelscope.cn/models/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice
