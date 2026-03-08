# openclaw-video-summary

中文：面向 OpenClaw 的视频总结工具。输入 YouTube / Bilibili 链接或本地视频，先下载到本地，再走 ASR 优先的总结链路，必要时自动升级到 `fusion` 进行画面证据增强。  
English: A video summarization tool for OpenClaw. It accepts YouTube / Bilibili URLs or local video files, materializes them locally first, runs an ASR-first summary pipeline, and upgrades to `fusion` only when visual evidence is likely useful.

## 概览 | Overview

中文：
- 默认模式是 `auto`
- 主流程是 `download/localize -> ASR -> timeline -> Chinese summary`
- 对纯口播类视频倾向保留 `fast`
- 对教程、演示、界面操作、图表解读类视频会倾向升级到 `fusion`
- 输出产物固定，可追溯，可复跑

English:
- Default mode is `auto`
- Main flow is `download/localize -> ASR -> timeline -> Chinese summary`
- Mostly verbal videos usually stay in `fast`
- Tutorials, demos, UI walkthroughs, and chart-heavy videos are more likely to upgrade to `fusion`
- Outputs are stable, traceable, and reproducible

## 核心能力 | Core Capabilities

中文：
- 支持输入：YouTube URL、Bilibili URL、本地视频文件
- 支持模式：`auto`、`fast`、`fusion`、`quality`
- 支持本地总结模板覆盖，用户可长期自定义输出风格
- 支持 `OpenAI-compatible` 接口
- 产物包括总结、时间线、转写、manifest，以及 `fusion` 的证据文件

English:
- Inputs: YouTube URL, Bilibili URL, local video file
- Modes: `auto`, `fast`, `fusion`, `quality`
- Supports persistent summary-template overrides
- Works with OpenAI-compatible APIs
- Produces summary, timeline, transcript, manifest, and `fusion` evidence artifacts

## 安装 | Installation

### 系统依赖 | System Dependencies

```bash
python3 --version
yt-dlp --version
ffmpeg -version
```

要求 | Required:
- `python >= 3.10`
- `yt-dlp`
- `ffmpeg`

### 项目安装 | Project Install

```bash
python3 -m pip install -e .
```

## 快速开始 | Quick Start

### CLI

```bash
python3 -m openclaw_video_summary.interfaces.cli summarize \
  "https://www.bilibili.com/video/BV..." \
  --mode auto \
  --output-root ./runs \
  --api-base "$OCVS_API_BASE" \
  --api-key "$OCVS_API_KEY" \
  --model glm-4.6v \
  --json-summary
```

中文：默认推荐直接用 `--mode auto`。  
English: `--mode auto` is the recommended default.

### OpenClaw 使用方式 | OpenClaw Usage

中文：
1. 直接贴 YouTube / Bilibili 链接
2. 工具先把视频下载到本地
3. 默认先跑 `auto`
4. 返回中文总结、时间线摘录、关键证据和产物路径

English:
1. Paste a YouTube / Bilibili link
2. The tool downloads the video locally first
3. It runs `auto` by default
4. It returns a Chinese summary, timeline excerpts, key evidence, and artifact paths

## 模式说明 | Modes

### `auto`

中文：
- 先完整跑一次 `fast`
- 再根据 transcript 和 timeline 判断是否有明显“画面价值”
- 如果是纯口播或画面增量很低，保留 `fast`
- 如果像教程、演示、操作步骤、图表解读，则升级到 `fusion`

English:
- Runs `fast` once first
- Uses transcript and timeline to decide whether visual evidence matters
- Keeps `fast` for talking-head / low-visual-value videos
- Upgrades to `fusion` for tutorials, demos, operational walkthroughs, and chart-driven content

Manifest 字段 | Manifest fields:
- `selected_mode`
- `auto_selection.reason`
- `auto_selection.signals`

### `fast`

中文：
- ASR 优先链路
- 生成转写、时间线和中文总结
- 速度更快，成本更低
- 适合口播、评论、访谈、播客式内容

English:
- ASR-first path
- Produces transcript, timeline, and Chinese summary
- Faster and cheaper
- Good for talking-head, commentary, interview, and podcast-like videos

### `fusion`

中文：
- 在 `fast` 基础上增加画面证据
- 当前实现是按视频分段再做多模态分析
- 适合教程、演示、界面操作、图表解读类视频
- 如果视觉链路失败，会自动降级回 `fast`

English:
- Adds visual evidence on top of `fast`
- Current implementation uses chunked video analysis
- Best for tutorials, demos, UI workflows, and chart-heavy videos
- Downgrades to `fast` when the visual path fails

### `quality`

中文：保留为质量优先扩展层，位于 `fusion` 之上。  
English: Reserved as a quality-first layer above `fusion`.

## Provider 配置 | Provider Configuration

中文：当前总结与多模态调用都走 OpenAI-compatible 接口。  
English: Both summary generation and multimodal analysis currently use an OpenAI-compatible interface.

环境变量 | Environment variables:

```bash
export OCVS_API_BASE="https://your-openai-compatible-endpoint"
export OCVS_API_KEY="your-api-key"
```

也可直接走 CLI 参数 | Or pass them through CLI flags:
- `--api-base`
- `--api-key`
- `--model`

## 自定义总结模板 | Custom Summary Template

中文：
现在支持长期自定义总结模版，不需要再改 Python 代码。

English:
Persistent summary-template customization is now supported without changing Python code.

覆盖优先级 | Override priority:
1. `OCVS_SUMMARY_TEMPLATE_FILE=/absolute/path/to/summary_prompt.md`
2. 仓库本地 `summary_prompt.local.md`
3. 全局 `~/.config/openclaw-video-summary/summary_prompt.md`
4. 内置默认模板  
   English: built-in default template

模板占位符 | Template placeholders:
- `{{visual_context}}`
- `{{timeline_brief}}`
- `{{transcript_text}}`

仓库本地快速开始 | Repo-local quick start:

```bash
cp summary_prompt.local.md.example summary_prompt.local.md
```

全局模板 | Global template:

```bash
mkdir -p ~/.config/openclaw-video-summary
cp summary_prompt.local.md.example ~/.config/openclaw-video-summary/summary_prompt.md
```

参考文件 | Reference files:
- [summary_prompt.local.md.example](summary_prompt.local.md.example)
- [summary_prompt.default.md](openclaw_video_summary/summary/summary_prompt.default.md)

## 产物契约 | Artifact Contract

中文：每次运行都会生成一个任务目录。  
English: Every run produces one task directory.

基础产物 | Base artifacts:
- `video.mp4`
- `summary_zh.md`
- `timeline.json`
- `transcript.json`
- `summarize_manifest.json`

增强模式附加产物 | Additional artifacts for enhanced modes:
- `evidence.json`
- `fusion_report.md`

中文：聊天输出应视为这些落盘文件的摘要视图。  
English: Chat responses should be treated as a summarized view of these saved artifacts.

## 降级行为 | Downgrade Behavior

中文：
- `fusion -> fast`
- `quality -> fusion`
- `quality -> fast`

English:
- `fusion -> fast`
- `quality -> fusion`
- `quality -> fast`

中文：降级信息会写入 manifest。  
English: Fallback metadata is written into the manifest.

## 测试 | Tests

### 单测 + 集成测试 | Unit + Integration

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py' -v
```

### 可选 E2E | Optional E2E

```bash
export OCVS_E2E=1
export OCVS_API_BASE="https://your-openai-compatible-endpoint"
export OCVS_API_KEY="your-api-key"
export OCVS_YOUTUBE_URL="https://www.youtube.com/watch?v=..."
export OCVS_BILIBILI_URL="https://www.bilibili.com/video/BV..."
```

运行 | Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.e2e.test_youtube_url -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.e2e.test_bilibili_url -v
```

## 当前限制 | Current Limitations

中文：
- 本地 ASR 在 CPU 环境下会比较慢
- `fusion` 的分段视频多模态请求时延较高
- 远端 provider 稳定性会直接影响 `fusion`
- 当前分支更适合持续迭代，不应过早宣称“生产就绪”

English:
- Local ASR can be slow on CPU-only environments
- Chunked multimodal requests in `fusion` can be latency-heavy
- Remote provider stability directly affects `fusion`
- This branch is suitable for ongoing iteration, not yet for strong “production-ready” claims

## 进一步说明 | More Detail

- 使用说明 | Usage guide: [docs/usage.md](docs/usage.md)
- Skill 合约 | Skill contract: [skill/SKILL.md](skill/SKILL.md)
