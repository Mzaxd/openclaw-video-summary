# openclaw-video-summary

默认文档语言：中文。English version: [README.en.md](README.en.md)

面向 OpenClaw 的视频总结工具。输入 YouTube / Bilibili 链接或本地视频，先下载到本地，再走 ASR 优先的总结链路，必要时自动升级到 `fusion` 进行画面证据增强。

## 概览

- 默认模式是 `auto`
- 主流程是 `download/localize -> ASR -> timeline -> Chinese summary`
- 对纯口播类视频倾向保留 `fast`
- 对教程、演示、界面操作、图表解读类视频会倾向升级到 `fusion`
- 输出产物固定，可追溯，可复跑

## 核心能力

- 支持输入：YouTube URL、Bilibili URL、本地视频文件
- 支持模式：`auto`、`fast`、`fusion`、`quality`
- 支持本地总结模板覆盖，用户可长期自定义输出风格
- 支持 `OpenAI-compatible` 接口
- 产物包括总结、时间线、转写、manifest，以及 `fusion` 的证据文件

## 安装

### 系统依赖

```bash
python3 --version
yt-dlp --version
ffmpeg -version
```

要求：
- `python >= 3.10`
- `yt-dlp`
- `ffmpeg`

### 项目安装

```bash
python3 -m pip install -e .
```

## 快速开始

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

默认推荐直接用 `--mode auto`。

### OpenClaw 使用方式

1. 直接贴 YouTube / Bilibili 链接
2. 工具先把视频下载到本地
3. 默认先跑 `auto`
4. 返回中文总结、时间线摘录、关键证据和产物路径

## 模式说明

### `auto`

- 先完整跑一次 `fast`
- 再根据 transcript 和 timeline 判断是否有明显“画面价值”
- 如果是纯口播或画面增量很低，保留 `fast`
- 如果像教程、演示、操作步骤、图表解读，则升级到 `fusion`

Manifest 关键字段：
- `selected_mode`
- `auto_selection.reason`
- `auto_selection.signals`

### `fast`

- ASR 优先链路
- 生成转写、时间线和中文总结
- 速度更快，成本更低
- 适合口播、评论、访谈、播客式内容

### `fusion`

- 在 `fast` 基础上增加画面证据
- 当前实现是按视频分段再做多模态分析
- 适合教程、演示、界面操作、图表解读类视频
- 如果视觉链路失败，会自动降级回 `fast`

### `quality`

保留为质量优先扩展层，位于 `fusion` 之上。

## Provider 配置

当前总结与多模态调用都走 OpenAI-compatible 接口。

环境变量：

```bash
export OCVS_API_BASE="https://your-openai-compatible-endpoint"
export OCVS_API_KEY="your-api-key"
```

也可直接走 CLI 参数：
- `--api-base`
- `--api-key`
- `--model`

## 自定义总结模板

现在支持长期自定义总结模版，不需要再改 Python 代码。

覆盖优先级：
1. `OCVS_SUMMARY_TEMPLATE_FILE=/absolute/path/to/summary_prompt.md`
2. 仓库本地 `summary_prompt.local.md`
3. 全局 `~/.config/openclaw-video-summary/summary_prompt.md`
4. 内置默认模板

模板占位符：
- `{{visual_context}}`
- `{{timeline_brief}}`
- `{{transcript_text}}`

仓库本地快速开始：

```bash
cp summary_prompt.local.md.example summary_prompt.local.md
```

全局模板：

```bash
mkdir -p ~/.config/openclaw-video-summary
cp summary_prompt.local.md.example ~/.config/openclaw-video-summary/summary_prompt.md
```

参考文件：
- [summary_prompt.local.md.example](summary_prompt.local.md.example)
- [summary_prompt.default.md](openclaw_video_summary/summary/summary_prompt.default.md)

## 产物契约

每次运行都会生成一个任务目录。

基础产物：
- `video.mp4`
- `summary_zh.md`
- `timeline.json`
- `transcript.json`
- `summarize_manifest.json`

增强模式附加产物：
- `evidence.json`
- `fusion_report.md`

聊天输出应视为这些落盘文件的摘要视图。

## 降级行为

- `fusion -> fast`
- `quality -> fusion`
- `quality -> fast`

降级信息会写入 manifest。

## 测试

### 单测 + 集成测试

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py' -v
```

### 可选 E2E

```bash
export OCVS_E2E=1
export OCVS_API_BASE="https://your-openai-compatible-endpoint"
export OCVS_API_KEY="your-api-key"
export OCVS_YOUTUBE_URL="https://www.youtube.com/watch?v=..."
export OCVS_BILIBILI_URL="https://www.bilibili.com/video/BV..."
```

运行：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.e2e.test_youtube_url -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.e2e.test_bilibili_url -v
```

## 当前限制

- 本地 ASR 在 CPU 环境下会比较慢
- `fusion` 的分段视频多模态请求时延较高
- 远端 provider 稳定性会直接影响 `fusion`
- 当前分支更适合持续迭代，不应过早宣称“生产就绪”

## 进一步说明

- 使用说明：[docs/usage.md](docs/usage.md)
- Skill 合约：[skill/SKILL.md](skill/SKILL.md)
