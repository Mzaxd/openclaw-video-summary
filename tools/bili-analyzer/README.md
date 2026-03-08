# bili-analyzer

轻量稳定的 B 站视频准备工具，主链路：

`yt-dlp 下载 -> ffmpeg 抽帧 -> 相邻帧去重(dHash)`

同时提供：
- CLI：`bili-analyzer`
- MCP Server：`bili-analyzer-mcp`（工具：`prepare_video`、`analyze_frames`）
- OpenClaw skill 文档封装（主路径切到 Python CLI）
- MVP 总结能力：`summarize`（支持 `fast` / `fusion`）

## 1) 安装

### 系统依赖

- `yt-dlp`
- `ffmpeg`
- Python `>=3.10`

macOS 示例：

```bash
brew install yt-dlp ffmpeg
```

### Python 安装

在 workspace 根目录执行：

```bash
pip install -e tools/bili-analyzer
```

如果要启用轻量 ASR（方案 B，faster-whisper）：

```bash
pip install -e 'tools/bili-analyzer[asr]'
```

安装完成后会有命令：

```bash
bili-analyzer --help
bili-analyzer-mcp
```

## 2) 快速开始

### CLI: prepare

```bash
bili-analyzer prepare "https://www.bilibili.com/video/BV1xxxx" -o ./tmp
```

可选参数：

- `--fps <float>` 默认 `1.0`
- `--similarity <0-1>` 默认 `0.80`
- `--no-dedup`
- `--video-only`
- `--frames-only`
- `--json-summary`（仅输出精简 JSON，便于脚本读取）

示例：

```bash
bili-analyzer prepare "https://www.bilibili.com/video/BV1xxxx" -o ./tmp --fps 0.5 --similarity 0.85
```

输出目录形态（示例）：

```text
tmp/
  bili-BV1xxxx/
    video.mp4
    images/
      frame_000001.jpg
      ...
      frames_index.json
    prepare_manifest.json
```

`prepare_manifest.json` 中会包含：
- `frame_counts`：统一口径的去重前/后数量
- `timings_sec`：下载、抽帧、去重、总耗时等阶段耗时

### analyze-frames

```bash
bili-analyzer analyze-frames ./tmp/bili-BV1xxxx/images
# 或精简输出
bili-analyzer analyze-frames ./tmp/bili-BV1xxxx/images --json-summary
```

### transcribe（方案 B：faster-whisper）

```bash
# input 可以是 prepare 目录（含 video.mp4）或视频文件路径
bili-analyzer transcribe ./tmp/bili-BV1xxxx --asr-model small --language zh --json-summary
```

产物：
- `audio_16k.wav`
- `transcript.json`（含全文 + 分段时间戳）

### summarize（MVP：视频归纳总结）

```bash
bili-analyzer summarize "https://www.bilibili.com/video/BV1xxxx" \
  -o ./tmp \
  --mode fast \
  --language auto \
  --llm-model glm-4.6v \
  --json-summary
```

说明：

- `--mode fast`：ASR-only 路径，稳定优先（默认）
- `--mode fusion`：ASR + 帧上下文融合；若融合失败会自动回退到 ASR-only
- `--language auto`：自动识别输入语种（支持英文视频输入，输出中文总结）

LLM 配置（二选一）：

```bash
export OPENAI_BASE_URL="https://your-openai-compatible-endpoint"
export OPENAI_API_KEY="your-key"
```

或通过参数传入：

```bash
--api-base ... --api-key ...
```

产物（位于任务目录）：

- `summary_zh.md`：中文总结
- `timeline.json`：时间线结构化输出
- `summarize_manifest.json`：流程元数据与回退信息

## 3) MCP 封装

### 本地启动

```bash
bili-analyzer-mcp
```

或：

```bash
python3 -m bili_analyzer.mcp_server
```

### 最小 MCP 配置示例

```json
{
  "mcpServers": {
    "bili-analyzer": {
      "command": "python3",
      "args": ["-m", "bili_analyzer.mcp_server"]
    }
  }
}
```

提供工具：
- `prepare_video(url, output, fps, similarity, no_dedup, video_only, frames_only)`
- `analyze_frames(images_dir)`

## 4) Smoke Test

```bash
bash tools/bili-analyzer/smoke_test.sh
```

该脚本会做参数与导入级别自检，不会默认下载真实视频。

## 5) 集成测试（最小）

```bash
python -m unittest discover -s tools/bili-analyzer/tests -p 'test_*.py' -v
```

当前包含：
- 成功场景：`analyze-frames --json-summary` 输出结构校验
- 失败场景：`prepare --similarity 1.5` 返回参数错误（exit code 2）
- `summarize` 时间线与回退逻辑单测
- E2E 模板（默认跳过）：真实 URL 路径，可通过环境变量启用

启用 E2E 模板测试（可选）：

```bash
BILI_E2E=1 BILI_TEST_URL='https://www.bilibili.com/video/BV1jRPsz4Ee3' \
python -m unittest discover -s tools/bili-analyzer/tests -p 'test_*.py' -v
```

单独运行 `summarize` E2E（建议）：

```bash
bili-analyzer summarize "https://www.bilibili.com/video/BV1jRPsz4Ee3" \
  -o ./tmp \
  --mode fusion \
  --language auto \
  --json-summary
```

## 6) FAQ

### Q1: 提示缺少 yt-dlp / ffmpeg

安装后确认可执行：

```bash
yt-dlp --version
ffmpeg -version
```

### Q2: `--similarity` 怎么选？

- 更高（如 `0.90`）：更激进去重，保留更少帧
- 更低（如 `0.70`）：更保守去重，保留更多细节

### Q3: `--video-only` 和 `--frames-only` 能一起用吗？

不能，CLI 会返回参数错误。

### Q4: transcribe 报错缺少 faster-whisper 怎么办？

安装 ASR 依赖：

```bash
pip install -e 'tools/bili-analyzer[asr]'
```

### Q5: 为什么用“图像帧分析”而不是“模型直接看视频”？

该工具定位是稳定的工程链路，优先保障可复现和可调试。后续可在此基础上增加原生视频模型路径。
