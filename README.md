# openclaw-video-summary

默认文档语言：中文。English version: [README.en.md](README.en.md)

把视频链接贴给 OpenClaw，自动下载、转写、总结，返回中文结果和可追溯产物。

## 给 OpenClaw 的最快安装方式（推荐）

直接使用安装手册：
- [docs/openclaw-install-for-ai.md](docs/openclaw-install-for-ai.md)

这份手册已经包含：
- macOS / Linux / Windows(WSL2) 自动分流安装
- OpenClaw + 系统依赖 + Python 依赖安装
- Skill 安装（workspace / 全局 / ClawHub）
- 一键验证与常见故障修复

## 3 步上手

### 1) 安装依赖与项目

```bash
python3 -m pip install -e .
python3 -m pip install -e 'tools/bili-analyzer[asr]'
```

### 2) 配置模型接口

```bash
export OCVS_API_BASE="https://your-openai-compatible-endpoint"
export OCVS_API_KEY="your-api-key"
```

### 3) 运行

```bash
python3 -m openclaw_video_summary.interfaces.cli summarize \
  "https://www.bilibili.com/video/BV..." \
  --mode auto \
  --platform-profile auto \
  --output-root ./runs \
  --api-base "$OCVS_API_BASE" \
  --api-key "$OCVS_API_KEY" \
  --json-summary
```

## 平台加速（ASR）

- 默认 `--platform-profile auto`：根据平台自动推断较优 `device/compute_type`
- 可手动指定：`--platform-profile apple_silicon|nvidia|intel|amd|cpu`
- 显式传 `--device` 或 `--compute-type` 时，会覆盖 profile 自动选择

## 为什么好用

- 简单：贴链接即可，默认 `auto` 自动选最合适模式
- 稳定：先落盘再总结，产物完整可复查
- 省心：失败自动降级，仍能给出可用结果

## 模板自定义（重点）

不改 Python 代码，也能长期定制总结风格。

覆盖优先级：
1. `OCVS_SUMMARY_TEMPLATE_FILE=/absolute/path/to/summary_prompt.md`
2. 仓库本地 `summary_prompt.local.md`
3. 全局 `~/.config/openclaw-video-summary/summary_prompt.md`
4. 内置默认模板

快速开始：

```bash
cp summary_prompt.local.md.example summary_prompt.local.md
```

模板占位符：
- `{{visual_context}}`
- `{{timeline_brief}}`
- `{{transcript_text}}`

参考：
- [summary_prompt.local.md.example](summary_prompt.local.md.example)
- [summary_prompt.default.md](openclaw_video_summary/summary/summary_prompt.default.md)

## 输出结果

每次运行会生成任务目录，核心文件：
- `summary_zh.md`
- `timeline.json`
- `transcript.json`
- `summarize_manifest.json`

## 技术细节（简版）

- 输入：YouTube / Bilibili / 本地视频
- 模式：`auto`（默认）、`fast`、`fusion`、`quality`
- 依赖：`python>=3.10`、`yt-dlp`、`ffmpeg`
- 接口：OpenAI-compatible

详细说明见：
- 使用手册：[docs/usage.md](docs/usage.md)
- Skill 合约：[skill/SKILL.md](skill/SKILL.md)
- 安装手册（给 OpenClaw）：[docs/openclaw-install-for-ai.md](docs/openclaw-install-for-ai.md)
