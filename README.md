# openclaw-video-summary

默认文档语言：中文。English version: [README.en.md](README.en.md)

把视频链接贴给 OpenClaw，脚本自动完成下载/字幕提取/转写/分段，最后由 OpenClaw 会话内模型基于模板完成中文总结。

## 给 OpenClaw 的最快安装方式（推荐）

直接使用安装手册：
- [skill/references/openclaw-install-for-ai.md](skill/references/openclaw-install-for-ai.md)

这份手册已经包含：
- macOS / Linux / Windows(WSL2) 自动分流安装
- OpenClaw + 系统依赖 + Python 依赖安装
- Skill 安装（workspace / 全局 / ClawHub）
- 一键验证与常见故障修复

## 3 步上手

### 1) 安装依赖

```bash
python3 -m pip install "faster-whisper>=1.0.0"
```

### 2) 运行

```bash
python3 skill/scripts/video_summary.py summarize \
  "https://www.bilibili.com/video/BV..." \
  --mode auto \
  --platform-profile auto \
  --output-root ./runs \
  --json-summary
```

## 平台加速（ASR）

- 默认 `--platform-profile auto`：根据平台自动推断较优 `device/compute_type`
- 可手动指定：`--platform-profile apple_silicon|nvidia|intel|amd|cpu`
- Apple Silicon 默认优先 `mlx-whisper`（Metal）；若未安装或运行失败会自动回退到 `faster-whisper(cpu)`
- 显式传 `--device` 或 `--compute-type` 时，会覆盖 profile 自动选择

## 为什么好用

- 简单：贴链接即可，默认 `auto` 自动选最合适模式
- 稳定：先落盘再总结，产物完整可复查
- 清晰：脚本不依赖外部 LLM，总结由 OpenClaw 在会话内完成

## 模板自定义（重点）

不改脚本逻辑，也能长期定制总结风格。

模板文件：
- `skill/templates/default.md`
- `skill/templates/tutorial.md`
- `skill/templates/interview.md`
- `skill/templates/review.md`
- `skill/templates/news.md`

规则文件：
- `skill/config/template_rules.json`
- 自动按关键词路由模板，也可用 `--template-type` 手动指定。

模板占位符：
- `{{visual_context}}`
- `{{timeline_brief}}`
- `{{transcript_text}}`

参考：
- 模板占位符：`{{visual_context}}` `{{timeline_brief}}` `{{transcript_text}}`

## 输出结果

每次运行会生成任务目录，核心文件：
- `summary_zh.md`
- `summary_task_prompt.md`
- `timeline.json`
- `transcript.json`
- `summarize_manifest.json`

## 技术细节（简版）

- 输入：YouTube / Bilibili / 本地视频
- 模式：`auto`（默认）、`fast`、`fusion`
- 依赖：`python>=3.10`、`yt-dlp`、`ffmpeg`
- 执行入口：`skill/scripts/video_summary.py`

详细说明见：
- 使用手册：[skill/references/usage.md](skill/references/usage.md)
- Skill 合约：[skill/SKILL.md](skill/SKILL.md)
- 安装手册（给 OpenClaw）：[skill/references/openclaw-install-for-ai.md](skill/references/openclaw-install-for-ai.md)
