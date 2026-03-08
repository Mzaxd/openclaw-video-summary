# OpenClaw AI Install Guide Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create `docs/openclaw-install-for-ai.md` so OpenClaw can auto-detect OS and complete install + skill setup + verification with minimal human input.

**Architecture:** Deliver a single operator guide with deterministic flow: detect environment, branch by OS, install dependencies, install project + ASR backend, install skill, configure provider, run validation, and recover from common failures. Keep one canonical command path per step and explicit success criteria to make AI execution robust.

**Tech Stack:** Markdown docs, shell commands (`bash/zsh`), OpenClaw CLI conventions, Python editable installs.

---

### Task 1: Prepare Documentation Skeleton

**Files:**
- Create: `docs/openclaw-install-for-ai.md`
- Reference: `README.md`
- Reference: `docs/usage.md`

**Step 1: Write the initial skeleton with required sections**

```md
# OpenClaw AI 安装指南（跨平台）

## 1. 目标与适用范围
## 2. 安装前自检（自动分流）
## 3. macOS 安装
## 4. Linux 安装
## 5. Windows 安装（WSL2 优先）
## 6. Python 依赖与项目安装
## 7. OpenClaw Skill 安装
## 8. API 与模板配置
## 9. 验证与成功判据
## 10. 常见错误与修复
## 11. 给 OpenClaw 的执行提示词
```

**Step 2: Run a quick content sanity check**

Run: `rg -n "^## " docs/openclaw-install-for-ai.md`
Expected: all 11 top-level sections listed once.

**Step 3: Commit**

```bash
git add docs/openclaw-install-for-ai.md
git commit -m "docs: scaffold OpenClaw AI install guide structure"
```

### Task 2: Implement Environment Detection and OS Branching

**Files:**
- Modify: `docs/openclaw-install-for-ai.md`

**Step 1: Add deterministic environment probe commands**

```bash
uname -s
command -v brew || true
command -v apt || true
command -v dnf || true
command -v pacman || true
python3 --version || true
openclaw --version || true
```

**Step 2: Add branch decision table**

- `Darwin -> macOS`
- `Linux + apt|dnf|pacman -> Linux`
- `Windows/MINGW/CYGWIN -> WSL2 path first`

**Step 3: Validate branch markers exist**

Run: `rg -n "Darwin|WSL2|apt|dnf|pacman" docs/openclaw-install-for-ai.md`
Expected: all branch keywords present.

**Step 4: Commit**

```bash
git add docs/openclaw-install-for-ai.md
git commit -m "docs: add environment detection and branching rules"
```

### Task 3: Add System Dependency Installation Per OS

**Files:**
- Modify: `docs/openclaw-install-for-ai.md`

**Step 1: Add macOS dependency commands**

```bash
brew update
brew install python@3.11 ffmpeg yt-dlp
python3 -m pip install -U pip setuptools wheel
```

**Step 2: Add Linux dependency commands (apt/dnf/pacman)**

```bash
sudo apt update && sudo apt install -y python3 python3-pip ffmpeg yt-dlp
sudo dnf install -y python3 python3-pip ffmpeg yt-dlp
sudo pacman -Sy --noconfirm python python-pip ffmpeg yt-dlp
```

**Step 3: Add Windows guidance with WSL2-first flow**

- Install/use WSL2 Ubuntu.
- Run Linux apt path inside WSL2.

**Step 4: Verify commands are present**

Run: `rg -n "brew install|apt install|dnf install|pacman -Sy|WSL2" docs/openclaw-install-for-ai.md`
Expected: all platforms covered.

**Step 5: Commit**

```bash
git add docs/openclaw-install-for-ai.md
git commit -m "docs: add cross-platform system dependency installation"
```

### Task 4: Add Project + ASR Installation Steps

**Files:**
- Modify: `docs/openclaw-install-for-ai.md`
- Reference: `pyproject.toml`
- Reference: `tools/bili-analyzer/pyproject.toml`

**Step 1: Add repository-root install commands**

```bash
python3 -m pip install -e .
python3 -m pip install -e 'tools/bili-analyzer[asr]'
```

**Step 2: Add dependency intent note**

- First command installs OpenClaw video summary CLI.
- Second command enables ASR backend (`faster-whisper`).

**Step 3: Validate both install commands exist**

Run: `rg -n "pip install -e \\.|tools/bili-analyzer\[asr\]" docs/openclaw-install-for-ai.md`
Expected: both commands present exactly once in install section.

**Step 4: Commit**

```bash
git add docs/openclaw-install-for-ai.md
git commit -m "docs: add project and ASR dependency installation steps"
```

### Task 5: Add OpenClaw Skill Installation Section

**Files:**
- Modify: `docs/openclaw-install-for-ai.md`
- Reference: `skill/SKILL.md`

**Step 1: Add workspace skill path method**

Document copy/sync from repo `skill/` to workspace `skills/openclaw-video-summary/`.

**Step 2: Add ClawHub method (optional)**

```bash
clawhub install <skill-slug>
```

**Step 3: Add skill precedence note**

- workspace `skills/` takes precedence over global `~/.openclaw/skills`.

**Step 4: Validate section completeness**

Run: `rg -n "skill/|skills/openclaw-video-summary|clawhub install|~/.openclaw/skills" docs/openclaw-install-for-ai.md`
Expected: all patterns present.

**Step 5: Commit**

```bash
git add docs/openclaw-install-for-ai.md
git commit -m "docs: add OpenClaw skill installation paths"
```

### Task 6: Add API/Template Config + End-to-End Verification

**Files:**
- Modify: `docs/openclaw-install-for-ai.md`
- Reference: `summary_prompt.local.md.example`

**Step 1: Add provider env configuration**

```bash
export OCVS_API_BASE="https://your-openai-compatible-endpoint"
export OCVS_API_KEY="your-api-key"
```

**Step 2: Add summarize verification command**

```bash
python3 -m openclaw_video_summary.interfaces.cli summarize "<video_or_url>" --mode auto --output-root ./runs --json-summary
```

**Step 3: Add artifact success criteria**

- `summary_zh.md`
- `timeline.json`
- `transcript.json`
- `summarize_manifest.json`

**Step 4: Verify section contains command + artifacts**

Run: `rg -n "OCVS_API_BASE|summarize .*--mode auto|summary_zh.md|timeline.json|transcript.json|summarize_manifest.json" docs/openclaw-install-for-ai.md`
Expected: all keys present.

**Step 5: Commit**

```bash
git add docs/openclaw-install-for-ai.md
git commit -m "docs: add API config and verification criteria"
```

### Task 7: Add Troubleshooting + OpenClaw Execution Prompt

**Files:**
- Modify: `docs/openclaw-install-for-ai.md`

**Step 1: Add troubleshooting matrix (problem -> signal -> fix -> recheck)**

Cover:
- missing `yt-dlp` / `ffmpeg`
- ASR backend install failure
- missing API causing local fallback
- skill not discovered

**Step 2: Add “Prompt for OpenClaw” section**

Prompt must require:
- detect OS first
- execute branch-specific steps in order
- report `command + output summary + pass/fail`
- auto-retry using troubleshooting section

**Step 3: Run doc quality checks**

Run: `rg -n "故障|排障|fallback|Prompt for OpenClaw|WSL2" docs/openclaw-install-for-ai.md`
Expected: troubleshooting and execution prompt both present.

**Step 4: Commit**

```bash
git add docs/openclaw-install-for-ai.md
git commit -m "docs: add troubleshooting matrix and OpenClaw execution prompt"
```

### Task 8: Final Consistency Pass and Evidence Capture

**Files:**
- Modify: `docs/openclaw-install-for-ai.md`
- Modify: `README.md` (optional, add link)

**Step 1: Verify all command blocks are copy-paste ready**

Run: `rg -n "```bash|python3 -m pip|openclaw_video_summary.interfaces.cli" docs/openclaw-install-for-ai.md`
Expected: every operational step has explicit command blocks.

**Step 2: Validate internal consistency with existing docs**

Run: `rg -n "auto|fusion|quality|summary_prompt.local.md" README.md docs/usage.md docs/openclaw-install-for-ai.md`
Expected: terminology matches existing project docs.

**Step 3: Final commit**

```bash
git add docs/openclaw-install-for-ai.md README.md
git commit -m "docs: finalize AI-operable OpenClaw installation guide"
```

