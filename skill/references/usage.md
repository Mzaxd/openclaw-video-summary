# OpenClaw Video Summary Usage

中文：这份文档偏操作手册，重点说明怎么运行、怎么理解输出、怎么覆盖模板、怎么读 `auto` 的决策结果。  
English: This document is an operator guide. It focuses on how to run the tool, interpret outputs, override templates, and understand `auto` mode decisions.

## 1. 入口 | Entrypoint

推荐入口 | Recommended entrypoint:

```bash
python3 skill/scripts/video_summary.py summarize <input>
```

支持输入 | Supported inputs:
- YouTube URL
- Bilibili URL
- 本地视频路径 | local video path

## 2. 默认行为 | Default Behavior

中文：
- 默认模式是 `auto`
- 工具会先把远程视频下载到本地
- 然后先跑一次 `fast`
- 再根据 transcript + timeline 判断是否需要升级到 `fusion`
- 脚本只生成总结任务与证据素材，最终总结由 OpenClaw 会话内模型完成

English:
- Default mode is `auto`
- Remote videos are downloaded locally first
- The tool runs `fast` once
- It then decides whether `fusion` is worth the extra cost
- The script only prepares summary tasks/artifacts; OpenClaw model does the final summary

## 3. 常用命令 | Common Commands

### 默认自动模式 | Default auto mode

```bash
python3 skill/scripts/video_summary.py summarize \
  "https://www.bilibili.com/video/BV..." \
  --output-root ./runs \
  --json-summary
```

### 强制 `fast`

```bash
python3 skill/scripts/video_summary.py summarize \
  "./sample.mp4" \
  --mode fast \
  --output-root ./runs
```

### 强制 `fusion`

```bash
python3 skill/scripts/video_summary.py summarize \
  "./sample.mp4" \
  --mode fusion \
  --chunk-sec 180 \
  --output-root ./runs
```

## 4. 常用参数 | Common Flags

- `--mode auto|fast|fusion`
- `--output-root <dir>`
- `--asr-model <tiny|base|small|...>`
- `--language <auto|zh|en|...>`
- `--platform-profile <auto|nvidia|apple_silicon|intel|amd|cpu>`
- `--device <auto|cpu|cuda>`
- `--compute-type <int8|float16|...>`
- `--window-sec <seconds>`
- `--chunk-sec <seconds>`
- `--template-type <auto|default|tutorial|interview|review|news>`
- `--cookies-from-browser <chrome|edge|firefox|...>`
- `--cookies-file </absolute/path/cookies.txt>`
- `--max-video-height <e.g. 480|720|1080, 0 means no limit>`
- `--json-summary`

Cookies env vars:
- `OCVS_COOKIES_FROM_BROWSER`
- `OCVS_COOKIES_FILE`

### 平台加速示例 | Platform Acceleration Examples

Apple Silicon:

```bash
python3 skill/scripts/video_summary.py summarize \
  "./sample.mp4" \
  --mode fast \
  --platform-profile apple_silicon \
  --output-root ./runs
```

NVIDIA:

```bash
python3 skill/scripts/video_summary.py summarize \
  "./sample.mp4" \
  --mode fast \
  --platform-profile nvidia \
  --output-root ./runs
```

CPU fallback:

```bash
python3 skill/scripts/video_summary.py summarize \
  "./sample.mp4" \
  --mode fast \
  --platform-profile cpu \
  --output-root ./runs
```

覆盖规则 | Override precedence:
- 如果显式传了 `--device` 或 `--compute-type`，优先使用显式参数
- 否则按 `--platform-profile` 进行自动/手动平台选择

Apple Silicon 行为 | Apple Silicon behavior:
- `--platform-profile apple_silicon` 会优先使用 `mlx-whisper`（Metal）
- 若 `mlx-whisper` 未安装或执行失败，会自动回退到 `faster-whisper(cpu)`
- manifest 可通过 `transcribe.engine` 与 `transcribe.runtime_profile` 查看最终落地路径

## 5. `auto` 如何判断 | How `auto` Decides

中文：
`auto` 目前是规则式判断，不是黑盒模型判别。它会在 transcript 和 timeline 中查找“视觉或操作信号”。

典型会倾向升级到 `fusion` 的信号：
- `界面`
- `页面`
- `按钮`
- `设置`
- `点击`
- `图表`
- `截图`
- `演示`
- `教程`
- `左边 / 右边 / 上方 / 下方`
- `如图 / 可以看到 / 展示 / 切换`

如果这些信号很弱，通常会保留在 `fast`。

English:
`auto` currently uses rule-based heuristics, not a separate classifier model. It scans transcript and timeline content for visual or operational cues.

Typical signals that push it toward `fusion`:
- `界面`
- `页面`
- `按钮`
- `设置`
- `点击`
- `图表`
- `截图`
- `演示`
- `教程`
- `左边 / 右边 / 上方 / 下方`
- `如图 / 可以看到 / 展示 / 切换`

If these signals are weak, it usually stays in `fast`.

## 6. 输出目录 | Output Directory

中文：每次运行都会在 `output-root/task-id/` 下生成一个任务目录。  
English: Each run creates a task directory under `output-root/task-id/`.

基础产物 | Base artifacts:
- `video.mp4`
- `summary_zh.md`
- `summary_task_prompt.md`
- `timeline.json`
- `transcript.json`
- `summarize_manifest.json`

增强产物 | Enhanced artifacts:
- `evidence.json`
- `fusion_report.md`
- `chunks/`（仅 `fusion` 路径）

## 7. 如何看 Manifest | How To Read the Manifest

重点字段 | Important fields:

- `mode`
  中文：请求模式。  
  English: The requested mode.

- `selected_mode`
  中文：最终实际落到的模式。  
  English: The final mode actually used.

- `summary_source`
  中文：总结产物来源标记，例如 `skill_prompt`、`skill_prompt_fusion`。  
  English: Summary artifact source marker, e.g. `skill_prompt` or `skill_prompt_fusion`.

- `fallback`
  中文：降级信息。  
  English: Fallback information.

- `auto_selection`
  中文：`auto` 的决策依据。  
  English: The reason and signals behind `auto` mode.

示例 | Example:

```json
{
  "mode": "auto",
  "selected_mode": "fusion",
  "summary_source": "skill_prompt_fusion",
  "auto_selection": {
    "reason": "detected strong visual or operational cues in transcript/timeline",
    "signals": ["pattern_2_hits=3", "pattern_3_hits=2"]
  }
}
```

## 8. 自定义总结模板 | Custom Summary Template

模板位置 | Template location:
- `skill/templates/default.md`
- `skill/templates/tutorial.md`
- `skill/templates/interview.md`
- `skill/templates/review.md`
- `skill/templates/news.md`

类型路由规则 | Type routing rules:
- `skill/config/template_rules.json`
- 命中规则后会在 manifest 写入 `template_type` 和 `template_file`
- 可用 `--template-type` 强制指定模板类型

模板占位符 | Template placeholders:
- `{{visual_context}}`
- `{{timeline_brief}}`
- `{{transcript_text}}`

## 9. OpenClaw 汇总模式 | OpenClaw Summary Mode

中文：脚本不再调用外部 LLM。请在 OpenClaw 会话中读取 `summary_task_prompt.md` 并生成最终总结。  
English: The script no longer calls external LLMs. Use `summary_task_prompt.md` in OpenClaw chat to produce the final summary.

## 10. 测试 | Testing

### 快速自检 | Quick Check

```bash
python3 skill/scripts/video_summary.py --help
python3 skill/scripts/video_summary.py summarize --help
```

### 可选真实输入验证 | Optional Real Input Check

```bash
export OCVS_YOUTUBE_URL="https://www.youtube.com/watch?v=..."
export OCVS_BILIBILI_URL="https://www.bilibili.com/video/BV..."
```

```bash
python3 skill/scripts/video_summary.py summarize "$OCVS_YOUTUBE_URL" --mode auto --output-root ./runs
python3 skill/scripts/video_summary.py summarize "$OCVS_BILIBILI_URL" --mode auto --output-root ./runs
```

## 11. 常见问题 | Common Notes

中文：
- 本地 CPU 跑 ASR 会慢，这是预期行为
- macOS Apple Silicon 建议安装 `mlx-whisper` 以启用 Metal 加速：
  `python3 -m pip install mlx-whisper`
- `fusion` 比 `fast` 慢很多，因为要做分段并生成画面理解任务
- 如果只想快速拿到稳定总结，优先 `auto` 或 `fast`

English:
- Local CPU ASR can be slow; this is expected
- `fusion` is much slower than `fast` because it prepares chunk-level visual analysis tasks
- If you want the fastest stable summary, prefer `auto` or `fast`
