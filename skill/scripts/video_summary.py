#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from bili_analyzer.core import _safe_slug_from_url, transcribe_video


VISUAL_PATTERNS = [
    re.compile(pattern)
    for pattern in (
        r"画面|镜头|字幕|动画|图表|表格|截图|示意图|流程图",
        r"界面|页面|屏幕|菜单|按钮|设置|左边|右边|上方|下方",
        r"点击|打开|选择|输入|拖动|安装|演示|教程|步骤|操作",
        r"可以看到|如图|这里|这边|对比|展示|切换",
    )
]

SYSTEM_PROMPT = "你是严谨的视频内容分析助手。你擅长把长视频整理成信息密度高、结构清楚、观点明确的中文总结。"


def _skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _templates_dir() -> Path:
    return _skill_root() / "templates"


def _rules_path() -> Path:
    return _skill_root() / "config" / "template_rules.json"


def load_template_rules() -> dict[str, Any]:
    rules_file = _rules_path()
    if not rules_file.exists():
        return {"default": "default", "rules": []}
    payload = json.loads(rules_file.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("template rules must be a JSON object")
    payload.setdefault("default", "default")
    payload.setdefault("rules", [])
    return payload


def detect_template_type(
    *,
    input_value: str,
    transcript_text: str,
    timeline: list[dict[str, Any]],
    rules: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    default_type = str(rules.get("default") or "default")
    haystack = " ".join(
        [
            input_value,
            transcript_text[:4000],
            "\n".join(str(item.get("summary") or "") for item in timeline[:10]),
        ]
    ).lower()
    best_type = default_type
    best_score = 0
    best_match: dict[str, Any] = {"rule": "default", "hits": []}
    for rule in list(rules.get("rules") or []):
        template_type = str(rule.get("type") or "").strip()
        keywords = [str(word).lower() for word in list(rule.get("keywords") or []) if str(word).strip()]
        min_hits = int(rule.get("min_hits") or 1)
        if not template_type or not keywords:
            continue
        hits = [word for word in keywords if word in haystack]
        if len(hits) >= min_hits and len(hits) > best_score:
            best_type = template_type
            best_score = len(hits)
            best_match = {"rule": template_type, "hits": hits}
    return best_type, best_match


def load_template_content(template_type: str) -> tuple[str, str]:
    normalized = (template_type or "default").strip().lower()
    template_path = _templates_dir() / f"{normalized}.md"
    if not template_path.exists():
        template_path = _templates_dir() / "default.md"
        normalized = "default"
    return normalized, template_path.read_text(encoding="utf-8")


def detect_source_kind(value: str) -> str:
    text = (value or "").strip()
    path = Path(text).expanduser()
    if path.exists() and path.is_file():
        return "local_file"
    if "youtube.com/" in text or "youtu.be/" in text:
        return "youtube"
    if "bilibili.com/" in text or "b23.tv/" in text:
        return "bilibili"
    raise ValueError(f"unsupported input source: {value}")


def extract_youtube_video_id(url: str) -> str:
    text = (url or "").strip()
    m = re.search(r"(?:v=|youtu\.be/|/shorts/)([A-Za-z0-9_-]{11})", text)
    if m:
        return m.group(1)
    return ""


def build_task_id(input_value: str, source_kind: str) -> str:
    if source_kind == "local_file":
        return Path(input_value).expanduser().stem
    if source_kind == "youtube":
        video_id = extract_youtube_video_id(input_value)
        if video_id:
            return f"yt-{video_id}"
        digest = hashlib.sha1(input_value.encode("utf-8")).hexdigest()[:12]
        return f"yt-{digest}"
    if source_kind == "bilibili":
        return _safe_slug_from_url(input_value)
    digest = hashlib.sha1(input_value.encode("utf-8")).hexdigest()[:12]
    return f"video-{digest}"


def parse_time_token(token: str) -> float:
    token = token.strip().replace(",", ".")
    parts = token.split(":")
    if len(parts) == 3:
        h, m, s = parts
        return float(h) * 3600 + float(m) * 60 + float(s)
    if len(parts) == 2:
        m, s = parts
        return float(m) * 60 + float(s)
    return float(parts[0])


def parse_subtitle_file(path: Path) -> dict[str, Any]:
    if path.suffix.lower() == ".xml":
        return parse_danmaku_xml(path)
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    segments: list[dict[str, Any]] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if "-->" not in line:
            i += 1
            continue
        left, right = [part.strip() for part in line.split("-->", 1)]
        start = parse_time_token(left.split(" ")[0])
        end = parse_time_token(right.split(" ")[0])
        i += 1
        cue_lines: list[str] = []
        while i < len(lines) and lines[i].strip():
            cue_lines.append(lines[i].strip())
            i += 1
        cue_text = re.sub(r"<[^>]+>", "", " ".join(cue_lines)).strip()
        if cue_text:
            segments.append({"start": round(start, 3), "end": round(end, 3), "text": cue_text})
    full_text = "\n".join(item["text"] for item in segments)
    return {"text": full_text, "segments": segments}


def parse_danmaku_xml(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return {"text": "", "segments": []}
    segments: list[dict[str, Any]] = []
    for node in root.findall(".//d"):
        payload = (node.attrib.get("p") or "").split(",")
        text = (node.text or "").strip()
        if not text:
            continue
        try:
            start = float(payload[0]) if payload and payload[0] else 0.0
        except ValueError:
            start = 0.0
        segments.append(
            {
                "start": round(start, 3),
                "end": round(start + 3.0, 3),
                "text": text,
            }
        )
    segments.sort(key=lambda item: (float(item.get("start") or 0.0), str(item.get("text") or "")))
    full_text = "\n".join(item["text"] for item in segments)
    return {"text": full_text, "segments": segments}


def probe_subtitle(
    input_value: str,
    output_dir: Path,
    *,
    timeout_sec: float = 8.0,
    cookies_from_browser: str = "",
    cookies_file: str = "",
) -> dict[str, Any]:
    if shutil.which("yt-dlp") is None:
        return {"status": "error", "reason": "yt-dlp-not-found", "subtitle_path": ""}
    with tempfile.TemporaryDirectory(prefix="ocvs-sub-") as td:
        temp_root = Path(td)
        cmd = [
            "yt-dlp",
            "--skip-download",
            "--no-part",
            "--no-warnings",
            "--write-subs",
            "--write-auto-subs",
            "--sub-langs",
            "all",
            "--sub-format",
            "vtt/srt/best",
            "-P",
            str(temp_root),
            "-o",
            "%(id)s.%(ext)s",
            input_value,
        ]
        cmd = apply_yt_dlp_cookies(
            cmd,
            cookies_from_browser=cookies_from_browser,
            cookies_file=cookies_file,
        )
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec)
        except Exception as exc:
            return {"status": "error", "reason": str(exc), "subtitle_path": ""}
        if proc.returncode != 0:
            return {"status": "miss", "reason": "subtitle_not_found", "subtitle_path": ""}
        candidates = sorted(
            path for path in temp_root.rglob("*") if path.suffix.lower() in {".vtt", ".srt", ".xml"}
        )
        if not candidates:
            return {"status": "miss", "reason": "subtitle_not_found", "subtitle_path": ""}
        preferred: Path | None = None
        for suffix in (".vtt", ".srt", ".xml"):
            for candidate in candidates:
                if candidate.suffix.lower() == suffix:
                    preferred = candidate
                    break
            if preferred is not None:
                break
        chosen = preferred or candidates[0]
        output_dir.mkdir(parents=True, exist_ok=True)
        final_path = output_dir / f"subtitle{chosen.suffix.lower()}"
        shutil.copy2(chosen, final_path)
        return {"status": "success", "reason": "", "subtitle_path": str(final_path)}


def probe_youtube_transcript_api(input_value: str, output_dir: Path) -> dict[str, Any]:
    video_id = extract_youtube_video_id(input_value)
    if not video_id:
        return {"status": "miss", "reason": "invalid_youtube_video_id", "subtitle_path": ""}
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except Exception:
        return {"status": "error", "reason": "youtube-transcript-api-not-installed", "subtitle_path": ""}

    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=["zh-Hans", "zh", "en"])
    except Exception as exc:
        return {"status": "miss", "reason": f"youtube-transcript-api-failed: {exc}", "subtitle_path": ""}

    if not transcript:
        return {"status": "miss", "reason": "empty_youtube_transcript", "subtitle_path": ""}

    output_dir.mkdir(parents=True, exist_ok=True)
    srt_path = output_dir / "subtitle.srt"
    lines: list[str] = []
    for index, item in enumerate(transcript, start=1):
        start = float(item.get("start") or 0.0)
        duration = float(item.get("duration") or 1.0)
        end = start + max(duration, 0.5)
        text = str(item.get("text") or "").replace("\n", " ").strip()
        if not text:
            continue
        lines.extend(
            [
                str(index),
                f"{_srt_time(start)} --> {_srt_time(end)}",
                text,
                "",
            ]
        )
    if not lines:
        return {"status": "miss", "reason": "empty_youtube_transcript_lines", "subtitle_path": ""}
    srt_path.write_text("\n".join(lines), encoding="utf-8")
    return {"status": "success", "reason": "", "subtitle_path": str(srt_path)}


def _srt_time(seconds: float) -> str:
    total_ms = max(int(round(seconds * 1000)), 0)
    h = total_ms // 3600000
    m = (total_ms % 3600000) // 60000
    s = (total_ms % 60000) // 1000
    ms = total_ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def download_to_video(
    input_value: str,
    target: Path,
    *,
    cookies_from_browser: str = "",
    cookies_file: str = "",
    max_video_height: int = 720,
) -> None:
    kind = detect_source_kind(input_value)
    target.parent.mkdir(parents=True, exist_ok=True)
    if kind == "local_file":
        shutil.copy2(Path(input_value).expanduser(), target)
        return
    if shutil.which("yt-dlp") is None:
        raise RuntimeError("yt-dlp is required to download remote videos")
    cmd = [
        "yt-dlp",
        "--no-part",
        "--force-overwrites",
        "--merge-output-format",
        "mp4",
        "-o",
        str(target),
    ]
    if max_video_height > 0:
        format_selector = f"bv*[height<={max_video_height}]+ba/b[height<={max_video_height}]/b"
        cmd.extend(["-f", format_selector])
    cmd.append(input_value)
    cmd = apply_yt_dlp_cookies(
        cmd,
        cookies_from_browser=cookies_from_browser,
        cookies_file=cookies_file,
    )
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        details = proc.stderr.strip() or proc.stdout.strip() or "yt-dlp failed"
        raise RuntimeError(details)


def apply_yt_dlp_cookies(
    cmd: list[str],
    *,
    cookies_from_browser: str,
    cookies_file: str,
) -> list[str]:
    final_cmd = list(cmd)
    if cookies_file:
        final_cmd.extend(["--cookies", cookies_file])
    elif cookies_from_browser:
        final_cmd.extend(["--cookies-from-browser", cookies_from_browser])
    return final_cmd


def build_timeline(segments: list[dict[str, Any]], window_sec: float) -> list[dict[str, Any]]:
    if not segments:
        return []
    windows: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    window_start = float(segments[0].get("start") or 0.0)
    for segment in segments:
        start = float(segment.get("start") or 0.0)
        if start - window_start >= window_sec and current:
            windows.append(current)
            current = []
            window_start = start
        current.append(segment)
    if current:
        windows.append(current)

    timeline: list[dict[str, Any]] = []
    for idx, items in enumerate(windows):
        start = float(items[0].get("start") or 0.0)
        end = float(items[-1].get("end") or start)
        text = " ".join(str(item.get("text") or "").strip() for item in items).strip()
        summary = text[:180] + ("..." if len(text) > 180 else "")
        timeline.append({"index": idx, "start": round(start, 3), "end": round(end, 3), "summary": summary})
    return timeline


def visual_score(text: str) -> tuple[int, list[str]]:
    score = 0
    signals: list[str] = []
    for index, pattern in enumerate(VISUAL_PATTERNS, start=1):
        hits = len(pattern.findall(text))
        if hits:
            score += min(hits, 3)
            signals.append(f"pattern_{index}_hits={hits}")
    return score, signals


def choose_mode(transcript: dict[str, Any], timeline: list[dict[str, Any]]) -> tuple[str, str, list[str]]:
    content = str(transcript.get("text") or "") + "\n" + "\n".join(item["summary"] for item in timeline[:12])
    score, signals = visual_score(content)
    if len(timeline) >= 6:
        score += 1
        signals.append(f"timeline_items={len(timeline)}")
    if score >= 4:
        return "fusion", "detected strong visual cues", signals
    return "fast", "transcript looks primarily verbal", signals or ["no_strong_visual_cues"]


def split_video_chunks(video_path: Path, chunks_dir: Path, chunk_sec: float) -> list[Path]:
    chunks_dir.mkdir(parents=True, exist_ok=True)
    pattern = chunks_dir / "chunk_%02d.mp4"
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-map",
        "0",
        "-c",
        "copy",
        "-f",
        "segment",
        "-segment_time",
        str(chunk_sec),
        "-reset_timestamps",
        "1",
        str(pattern),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        details = proc.stderr.strip() or proc.stdout.strip() or "ffmpeg segment failed"
        raise RuntimeError(details)
    return sorted(chunks_dir.glob("chunk_*.mp4"))


def build_prompt(
    *,
    transcript_text: str,
    timeline: list[dict[str, Any]],
    visual_context: dict[str, Any] | None,
    template_text: str,
) -> str:
    timeline_brief = [
        {"start": item.get("start"), "end": item.get("end"), "summary": item.get("summary")}
        for item in timeline[:20]
    ]
    visual_json = "无" if not visual_context else json.dumps(visual_context, ensure_ascii=False, indent=2)
    user_prompt = (
        template_text.replace("{{visual_context}}", visual_json)
        .replace("{{timeline_brief}}", json.dumps(timeline_brief, ensure_ascii=False, indent=2))
        .replace("{{transcript_text}}", transcript_text[:18000])
    )
    return (
        "# OpenClaw Summary Task\n\n"
        "请在当前会话中使用你的模型能力完成总结，不要调用外部 AI 服务。\n\n"
        "## System Prompt\n"
        f"{SYSTEM_PROMPT}\n\n"
        "## User Prompt\n"
        f"{user_prompt}\n"
    )


def run_summarize(args: argparse.Namespace) -> dict[str, Any]:
    started = time.perf_counter()
    source_kind = detect_source_kind(args.input_value)
    task_id = build_task_id(args.input_value, source_kind)
    task_dir = Path(args.output_root).expanduser() / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    video_path = task_dir / "video.mp4"
    transcript_json = task_dir / "transcript.json"
    timeline_json = task_dir / "timeline.json"
    summary_md = task_dir / "summary_zh.md"
    summary_prompt_md = task_dir / "summary_task_prompt.md"
    manifest_json = task_dir / "summarize_manifest.json"

    subtitle_probe: dict[str, Any] = {"attempted": False, "success": False, "reason": ""}
    asr_error = ""
    asr_result: dict[str, Any] | None = None
    transcript_source = "asr"
    transcript: dict[str, Any]

    cookies_from_browser = (args.cookies_from_browser or os.environ.get("OCVS_COOKIES_FROM_BROWSER") or "").strip()
    cookies_file = (args.cookies_file or os.environ.get("OCVS_COOKIES_FILE") or "").strip()

    if source_kind in {"youtube", "bilibili"}:
        subtitle_probe["attempted"] = True
        probe = probe_subtitle(
            args.input_value,
            task_dir,
            cookies_from_browser=cookies_from_browser,
            cookies_file=cookies_file,
        )
        subtitle_probe["provider"] = "yt-dlp"
        if probe.get("status") != "success" and source_kind == "youtube":
            api_probe = probe_youtube_transcript_api(args.input_value, task_dir)
            if api_probe.get("status") == "success":
                probe = api_probe
                subtitle_probe["provider"] = "youtube-transcript-api"
            else:
                subtitle_probe["provider"] = "yt-dlp+youtube-transcript-api"
                subtitle_probe["fallback_reason"] = api_probe.get("reason") or ""
        subtitle_probe.update(
            {
                "success": probe.get("status") == "success",
                "reason": probe.get("reason") or "",
                "subtitle_path": probe.get("subtitle_path") or "",
            }
        )
        if probe.get("status") == "success" and probe.get("subtitle_path"):
            if not video_path.exists():
                download_to_video(
                    args.input_value,
                    video_path,
                    cookies_from_browser=cookies_from_browser,
                    cookies_file=cookies_file,
                    max_video_height=args.max_video_height,
                )
            transcript = parse_subtitle_file(Path(str(probe["subtitle_path"])))
            transcript_json.write_text(json.dumps(transcript, ensure_ascii=False, indent=2), encoding="utf-8")
            transcript_source = "subtitle"
        else:
            download_to_video(
                args.input_value,
                video_path,
                cookies_from_browser=cookies_from_browser,
                cookies_file=cookies_file,
                max_video_height=args.max_video_height,
            )
            try:
                asr_result = transcribe_video(
                    input_path=str(video_path),
                    output=str(task_dir),
                    asr_model=args.asr_model,
                    language=None if args.language == "auto" else args.language,
                    device=args.device,
                    compute_type=args.compute_type,
                    platform_profile=args.platform_profile,
                )
                transcript = json.loads(Path(asr_result["transcript_file"]).read_text(encoding="utf-8"))
            except Exception as exc:
                asr_error = str(exc)
                transcript = {"text": "", "segments": []}
                transcript_json.write_text(json.dumps(transcript, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        download_to_video(
            args.input_value,
            video_path,
            cookies_from_browser=cookies_from_browser,
            cookies_file=cookies_file,
            max_video_height=args.max_video_height,
        )
        try:
            asr_result = transcribe_video(
                input_path=str(video_path),
                output=str(task_dir),
                asr_model=args.asr_model,
                language=None if args.language == "auto" else args.language,
                device=args.device,
                compute_type=args.compute_type,
                platform_profile=args.platform_profile,
            )
            transcript = json.loads(Path(asr_result["transcript_file"]).read_text(encoding="utf-8"))
        except Exception as exc:
            asr_error = str(exc)
            transcript = {"text": "", "segments": []}
            transcript_json.write_text(json.dumps(transcript, ensure_ascii=False, indent=2), encoding="utf-8")

    segments = list(transcript.get("segments") or [])
    timeline = build_timeline(segments, args.window_sec)
    timeline_json.write_text(
        json.dumps({"timeline": timeline, "meta": {"window_sec": args.window_sec, "segments": len(segments)}}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    requested_mode = args.mode
    selected_mode = requested_mode
    selection_reason = ""
    selection_signals: list[str] = []
    if requested_mode == "auto":
        selected_mode, selection_reason, selection_signals = choose_mode(transcript, timeline)

    evidence_path = task_dir / "evidence.json"
    fusion_report = task_dir / "fusion_report.md"
    visual_context: dict[str, Any] | None = None
    if selected_mode == "fusion":
        if not video_path.exists():
            download_to_video(
                args.input_value,
                video_path,
                cookies_from_browser=cookies_from_browser,
                cookies_file=cookies_file,
                max_video_height=args.max_video_height,
            )
        chunks = split_video_chunks(video_path, task_dir / "chunks", args.chunk_sec)
        items = []
        report_lines = ["# Fusion Chunk Tasks", ""]
        for idx, chunk in enumerate(chunks):
            prompt = (
                "请分析这个视频片段：先写画面摘要，再写和口播一致性，再给1-3条关键证据。"
                f"\n片段: {chunk.name}"
            )
            item = {
                "chunk": idx,
                "chunk_path": str(chunk),
                "start": round(idx * args.chunk_sec, 3),
                "end": round((idx + 1) * args.chunk_sec, 3),
                "observation": "待 OpenClaw 模型分析该片段",
                "confidence": "pending",
                "analysis_prompt": prompt,
            }
            items.append(item)
            report_lines.extend([f"## Chunk {idx}", "", f"- path: {chunk}", "- task: analyze visual content", "", f"prompt:\n{prompt}", ""])
        evidence_path.write_text(json.dumps({"items": items, "count": len(items)}, ensure_ascii=False, indent=2), encoding="utf-8")
        fusion_report.write_text("\n".join(report_lines).strip() + "\n", encoding="utf-8")
        visual_context = {"mode": "fusion", "chunk_sec": args.chunk_sec, "evidence_count": len(items), "evidence": items}

    transcript_text = str(transcript.get("text") or "")
    template_rules = load_template_rules()
    if args.template_type == "auto":
        template_type, template_match = detect_template_type(
            input_value=args.input_value,
            transcript_text=transcript_text,
            timeline=timeline,
            rules=template_rules,
        )
    else:
        template_type = args.template_type
        template_match = {"rule": "manual_override", "hits": [args.template_type]}
    resolved_template_type, template_text = load_template_content(template_type)
    summary_prompt = build_prompt(
        transcript_text=transcript_text,
        timeline=timeline,
        visual_context=visual_context,
        template_text=template_text,
    )
    summary_prompt_md.write_text(summary_prompt, encoding="utf-8")
    summary_md.write_text(
        (
            "# 视频中文总结（待 OpenClaw 生成）\n\n"
            f"- 请读取 `{summary_prompt_md.name}` 并在会话内完成总结。\n"
            "- 当前文件是占位说明，不是最终总结。\n"
            + (f"- 注意：ASR 失败，原因：{asr_error}\n" if asr_error else "")
        ),
        encoding="utf-8",
    )

    manifest = {
        "url": args.input_value,
        "mode": requested_mode,
        "selected_mode": selected_mode,
        "summary_source": "skill_prompt_fusion" if selected_mode == "fusion" else "skill_prompt",
        "template_type": resolved_template_type,
        "template_file": str(_templates_dir() / f"{resolved_template_type}.md"),
        "template_match": template_match,
        "task_root": str(task_dir),
        "task_id": task_id,
        "summary_zh_md": str(summary_md),
        "summary_prompt_md": str(summary_prompt_md),
        "timeline_json": str(timeline_json),
        "transcript_json": str(transcript_json),
        "source_kind": source_kind,
        "transcript_source": transcript_source,
        "subtitle_probe": subtitle_probe,
        "asr_error": asr_error or None,
        "transcribe": asr_result,
        "cookies_mode": (
            "cookies_file" if cookies_file else "cookies_from_browser" if cookies_from_browser else "none"
        ),
        "download_max_video_height": args.max_video_height,
        "auto_selection": {
            "reason": selection_reason,
            "signals": selection_signals,
        }
        if requested_mode == "auto"
        else None,
        "timings_sec": {"total_sec": round(time.perf_counter() - started, 3)},
    }
    manifest_json.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "mode": requested_mode,
        "selected_mode": selected_mode,
        "task_id": task_id,
        "task_dir": str(task_dir),
        "video_path": str(video_path),
        "summary_md": str(summary_md),
        "summary_prompt_md": str(summary_prompt_md),
        "timeline_json": str(timeline_json),
        "transcript_json": str(transcript_json),
        "run_manifest_json": str(manifest_json),
        "source_kind": source_kind,
        "summary_source": manifest["summary_source"],
        "template_type": manifest["template_type"],
        "template_file": manifest["template_file"],
        "evidence_json": str(evidence_path) if evidence_path.exists() else "",
        "fusion_report_md": str(fusion_report) if fusion_report.exists() else "",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="skill-video-summary", description="Skill-local video summarization prep")
    sub = parser.add_subparsers(dest="command", required=True)
    summarize = sub.add_parser("summarize", help="Prepare summary artifacts for OpenClaw")
    summarize.add_argument("input_value", help="Video URL or local file path")
    summarize.add_argument("-o", "--output-root", default="./runs", help="Run output root")
    summarize.add_argument("--mode", choices=["auto", "fast", "fusion"], default="auto")
    summarize.add_argument("--language", default="auto")
    summarize.add_argument("--asr-model", default="small")
    summarize.add_argument("--device", default=None)
    summarize.add_argument("--compute-type", default=None)
    summarize.add_argument("--platform-profile", default="auto")
    summarize.add_argument("--window-sec", type=float, default=90.0)
    summarize.add_argument("--chunk-sec", type=float, default=180.0)
    summarize.add_argument("--template-type", default="auto", help="Template type: auto/default/tutorial/interview/review/news")
    summarize.add_argument("--cookies-from-browser", default="", help="Pass browser cookies to yt-dlp, e.g. chrome")
    summarize.add_argument("--cookies-file", default="", help="Path to Netscape-format cookies.txt for yt-dlp")
    summarize.add_argument(
        "--max-video-height",
        type=int,
        default=720,
        help="Limit remote download height in yt-dlp (0 disables limit)",
    )
    summarize.add_argument("--json-summary", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command != "summarize":
        parser.error(f"unsupported command: {args.command}")
    result = run_summarize(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
