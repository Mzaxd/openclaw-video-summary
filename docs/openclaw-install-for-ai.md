# OpenClaw AI 安装手册（跨平台自动分流）

本文档用于直接交给 OpenClaw/AI 执行。目标是让 AI 在 `macOS / Linux / Windows(WSL2)` 自动选择路径并完成安装：

- OpenClaw CLI（如本机未安装）
- 系统依赖（`ffmpeg`、`yt-dlp`、Python）
- 项目依赖（`openclaw-video-summary` + `bili-analyzer[asr]`）
- Skill 安装（workspace 路径优先）
- 运行验证与排障

## 1. 目标与适用范围

- 适用项目根目录：`openclaw-video-summary`
- 适用系统：macOS、Linux、Windows（推荐 WSL2）
- Python 要求：`>=3.10`
- 外部命令要求：`ffmpeg`、`yt-dlp`

## 2. 安装前自检（AI 必须先执行）

在终端执行：

```bash
set -e
uname -s || true
command -v brew || true
command -v apt || true
command -v dnf || true
command -v pacman || true
python3 --version || true
node --version || true
npm --version || true
openclaw --version || true
```

分流规则：

- `uname -s = Darwin`：走 macOS 分支
- `uname -s = Linux`：走 Linux 分支（按 `apt/dnf/pacman` 自动选）
- Windows：优先 WSL2（Ubuntu）分支

## 3. OpenClaw CLI 安装（如未安装）

若 `openclaw --version` 失败，先安装 OpenClaw。

### 3.1 macOS / Linux / WSL2

```bash
curl -fsSL https://openclaw.ai/install.sh | bash
```

### 3.2 Windows PowerShell（非 WSL2）

```powershell
iwr -useb https://openclaw.ai/install.ps1 | iex
```

安装后建议执行：

```bash
openclaw doctor
openclaw status
```

## 4. 系统依赖安装（按 OS 分支）

### 4.1 macOS（Homebrew）

```bash
brew update
brew install python@3.11 ffmpeg yt-dlp
python3 -m pip install -U pip setuptools wheel
```

### 4.2 Linux（按包管理器）

#### apt（Ubuntu/Debian）

```bash
sudo apt update
sudo apt install -y python3 python3-pip ffmpeg yt-dlp
python3 -m pip install -U pip setuptools wheel
```

#### dnf（Fedora/RHEL）

```bash
sudo dnf install -y python3 python3-pip ffmpeg yt-dlp
python3 -m pip install -U pip setuptools wheel
```

#### pacman（Arch）

```bash
sudo pacman -Sy --noconfirm python python-pip ffmpeg yt-dlp
python3 -m pip install -U pip setuptools wheel
```

### 4.3 Windows（推荐 WSL2 Ubuntu）

在 WSL2 Ubuntu 中执行 `apt` 分支命令（见 4.2）。

## 5. 项目依赖安装（在仓库根目录执行）

确保当前目录是项目根目录（包含 `pyproject.toml`）。

```bash
python3 -m pip install -e .
python3 -m pip install -e 'tools/bili-analyzer[asr]'
```

如果是 macOS Apple Silicon，建议额外安装（启用 Metal ASR 加速）：

```bash
python3 -m pip install mlx-whisper
```

说明：

- `-e .` 安装 `openclaw-video-summary` CLI 入口
- `tools/bili-analyzer[asr]` 安装 ASR 后端（含 `faster-whisper`）
- Apple Silicon 会优先尝试 `mlx-whisper`，失败时自动回退 `faster-whisper(cpu)`

## 6. OpenClaw Skill 安装

> 本项目 Skill 源目录：`skill/`

### 6.1 方式 A（推荐）：安装到当前 OpenClaw workspace

在当前项目中创建 workspace skills 目录并复制：

```bash
mkdir -p ./.openclaw/skills/openclaw-video-summary
cp -R ./skill/. ./.openclaw/skills/openclaw-video-summary/
```

开新会话让 OpenClaw 重新加载 skills。

### 6.2 方式 B：安装到全局 managed skills

```bash
mkdir -p ~/.openclaw/skills/openclaw-video-summary
cp -R ./skill/. ~/.openclaw/skills/openclaw-video-summary/
```

优先级（高到低）：

1. `<workspace>/.openclaw/skills`
2. `~/.openclaw/skills`
3. bundled skills

### 6.3 方式 C（可选）：ClawHub

如果此 skill 已发布到 ClawHub：

```bash
npm i -g clawhub
clawhub search "openclaw video summary"
clawhub install <skill-slug>
```

## 7. Provider 与模板配置

### 7.1 配置 OpenAI-compatible 接口

```bash
export OCVS_API_BASE="https://your-openai-compatible-endpoint"
export OCVS_API_KEY="your-api-key"
```

### 7.2 可选：自定义总结模板

```bash
cp summary_prompt.local.md.example summary_prompt.local.md
```

或指定绝对路径：

```bash
export OCVS_SUMMARY_TEMPLATE_FILE="/absolute/path/to/summary_prompt.md"
```

## 8. 验证与成功判据

### 8.1 基础检查

```bash
yt-dlp --version
ffmpeg -version
python3 -c "import openclaw_video_summary; print('openclaw_video_summary ok')"
python3 -c "import bili_analyzer; print('bili_analyzer ok')"
python3 -c "import mlx_whisper; print('mlx_whisper ok')" || true
```

### 8.2 最小执行验证

```bash
python3 -m openclaw_video_summary.interfaces.cli summarize \
  "<video_or_url>" \
  --mode auto \
  --output-root ./runs \
  --api-base "$OCVS_API_BASE" \
  --api-key "$OCVS_API_KEY" \
  --json-summary
```

### 8.3 成功标准

命令成功后，任务目录下应至少存在：

- `summary_zh.md`
- `timeline.json`
- `transcript.json`
- `summarize_manifest.json`

可选增强产物：

- `evidence.json`
- `fusion_report.md`

## 9. 常见错误与修复

### 9.1 `yt-dlp is required` 或命令不存在

修复：按第 4 节安装 `yt-dlp`，再运行：

```bash
yt-dlp --version
```

### 9.2 `ffmpeg` 不存在或抽帧失败

修复：按第 4 节安装 `ffmpeg`，再运行：

```bash
ffmpeg -version
```

### 9.3 `No module named faster_whisper` 或 ASR 初始化失败

修复：

```bash
python3 -m pip install -e 'tools/bili-analyzer[asr]'
```

重试最小验证命令。

### 9.6 Apple Silicon 未走硬件加速

症状：manifest 中 `transcribe.engine` 不是 `mlx-whisper`。

修复：

```bash
python3 -m pip install -U mlx-whisper
```

说明：若 `mlx-whisper` 不可用，系统会自动回退到 `faster-whisper(cpu)`，功能可用但速度较慢。

### 9.4 输出里出现 `summary_source: local_fallback`

原因：API 未配置或 LLM 请求失败。

修复：确认 `OCVS_API_BASE`、`OCVS_API_KEY`，然后重跑。

### 9.5 skill 未生效

确认复制路径是否正确，并重开 OpenClaw 会话。重点检查：

- `./.openclaw/skills/openclaw-video-summary/SKILL.md`
- `~/.openclaw/skills/openclaw-video-summary/SKILL.md`

## 10. 给 OpenClaw 的执行提示词（可直接复制）

```text
你是安装执行代理。严格按 docs/openclaw-install-for-ai.md 执行：
1) 先运行“安装前自检”，识别当前 OS 与包管理器。
2) 按分支执行安装，不得跨分支混用命令。
3) 每一步输出：执行命令、关键输出、通过/失败结论。
4) 若失败，必须先使用第 9 节对应排障路径修复，再继续后续步骤。
5) 完成后输出最终验收报告：
   - OpenClaw 是否可用
   - 依赖是否齐全（yt-dlp/ffmpeg/python）
   - skill 是否加载
   - summarize 是否成功
   - 产物路径与文件列表
```

## 11. 官方参考链接

- OpenClaw Install: https://docs.openclaw.ai/install/index
- OpenClaw Skills: https://docs.openclaw.ai/tools/skills
- OpenClaw ClawHub: https://docs.openclaw.ai/tools/clawhub
- OpenClaw CLI Reference: https://docs.openclaw.ai/cli
