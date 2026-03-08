# OpenClaw 安装说明文档设计（面向 AI 自动执行）

- 日期：2026-03-08
- 项目：openclaw-video-summary
- 目标：产出一份可直接交给 OpenClaw 的安装文档，让 AI 自动识别操作系统并完成安装、skill 接入、配置与验证。

## 1. 背景与问题

当前仓库已经具备可运行能力，但安装前提分散在多个位置：

- 主项目 `pyproject.toml` 仅声明基础包信息，运行依赖没有完整集中声明。
- 实际 ASR 与分析依赖位于 `tools/bili-analyzer`（含 `faster-whisper` 可选依赖）。
- 还依赖系统二进制：`yt-dlp`、`ffmpeg`。

因此需要一份“文档驱动安装”方案，确保 OpenClaw/AI 在不同系统上可稳定执行。

## 2. 设计目标

1. 单文档覆盖 `macOS / Linux / Windows(WSL2优先)` 三种环境。
2. AI 先执行环境探测，再按分支安装，避免误装。
3. 明确包含 OpenClaw skill 安装步骤（workspace 与 ClawHub 两条路径）。
4. 提供可验证的成功判据（命令输出 + 产物文件）。
5. 提供最小排障闭环，失败时可继续推进而不是中断。

## 3. 非目标

- 不在本阶段改造项目打包结构（例如发布到 PyPI）。
- 不在本阶段实现“一键安装脚本”。
- 不在本阶段重构依赖声明体系。

## 4. 方案选型

已评估方案：

1. 单文档统一分流（推荐）
2. 三文档按系统拆分
3. 脚本优先 + 极简文档

选择方案 1，原因：

- 对 AI 执行最稳，入口唯一。
- 可以在同一文档中固定“先探测再分支”的流程。
- skill 安装、配置、验证这些跨系统共性步骤不易遗漏。

## 5. 文档信息架构

目标实施文档：`docs/openclaw-install-for-ai.md`

章节结构：

1. 目标与适用范围
2. 安装前自检（OS/包管理器/Python/OpenClaw/关键命令）
3. 按系统安装
   - macOS（brew）
   - Linux（apt/dnf/pacman）
   - Windows（WSL2 路径优先，原生兜底）
4. Python 与项目依赖安装
   - `pip install -e .`
   - `pip install -e 'tools/bili-analyzer[asr]'`
5. OpenClaw skill 安装
   - workspace `skills/` 路径
   - ClawHub 安装路径（如可用）
6. Provider/API 与模板配置
7. 验证与成功判据
8. 失败处理与排障
9. 给 OpenClaw 的执行提示词（严格执行模式）

## 6. 数据流与执行流

### 6.1 执行流

1. AI 运行环境探测命令。
2. 根据探测结果选择系统安装分支。
3. 安装系统依赖（`ffmpeg`、`yt-dlp`、Python 工具链）。
4. 安装项目 Python 依赖（主包 + ASR 可选依赖）。
5. 安装/挂载 skill 到 OpenClaw。
6. 写入 API 配置（环境变量）。
7. 执行最小验证任务并检查产物。
8. 若失败，按排障章修复后回到验证步骤。

### 6.2 成功输出

- 命令层：`yt-dlp --version`、`ffmpeg -version`、import 检查通过。
- 运行层：`summarize` 命令成功，输出 JSON。
- 文件层：存在 `summary_zh.md`、`timeline.json`、`transcript.json`、`summarize_manifest.json`。

## 7. 错误处理策略

至少覆盖以下错误：

1. 缺少 `yt-dlp` / `ffmpeg`
2. `faster-whisper` 安装失败（编译/平台问题）
3. API 未配置触发 `local_fallback`
4. skill 路径错误或未被 OpenClaw 发现

每类错误需给出：

- 识别信号（常见报错片段）
- 修复命令
- 修复后的验证命令

## 8. 兼容性与约束

- Python `>=3.10`。
- Windows 默认推荐 WSL2 Ubuntu，减少原生路径差异。
- OpenClaw 版本以官方文档为准；文档中应附官方链接。

## 9. 参考依据（官方）

- Skills: https://docs.openclaw.ai/skills
- Plugin: https://docs.openclaw.ai/tools/plugin
- ClawHub: https://docs.openclaw.ai/clawhub

## 10. 测试策略（文档级）

1. 在三种环境中至少各执行一次“从零安装 + 验证”。
2. 确认 AI 在未人工干预情况下可根据探测结果选对分支。
3. 故意制造一个失败场景（例如 unset API）验证排障段可恢复。

## 11. 风险与缓解

- 风险：不同 Linux 发行版包名差异。
  - 缓解：按包管理器分支提供命令，不写单一发行版命令。
- 风险：OpenClaw 本地路径布局不同。
  - 缓解：skill 安装提供 workspace 和 ClawHub 两条路径。
- 风险：外部模型服务不稳定。
  - 缓解：文档明确 `local_fallback` 预期与重试策略。

## 12. 实施产物定义

- 本阶段产物：本设计文档。
- 下一阶段产物：`docs/openclaw-install-for-ai.md`（可执行安装手册）。

