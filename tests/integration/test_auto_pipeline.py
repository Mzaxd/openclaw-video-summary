from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest


class AutoPipelineTest(unittest.TestCase):
    def test_run_auto_keeps_fast_for_talking_head_video(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)

            import openclaw_video_summary.pipeline.auto as auto_module
            from openclaw_video_summary.pipeline.fast import FastRunResult

            original_run_fast = auto_module._run_fast_pipeline
            original_run_fusion = auto_module._run_fusion_from_fast
            try:
                def fake_run_fast(input_value: str, *, output_root: Path | str, **_: object):
                    task_dir = Path(output_root) / "run-auto-fast"
                    task_dir.mkdir(parents=True, exist_ok=True)
                    video_path = task_dir / "video.mp4"
                    summary_md = task_dir / "summary_zh.md"
                    timeline_json = task_dir / "timeline.json"
                    transcript_json = task_dir / "transcript.json"
                    run_manifest_json = task_dir / "summarize_manifest.json"
                    video_path.write_bytes(b"video")
                    summary_md.write_text("# Summary\n", encoding="utf-8")
                    timeline_json.write_text(
                        json.dumps({"timeline": [{"start": 0, "end": 60, "summary": "讨论AI风险"}]}),
                        encoding="utf-8",
                    )
                    transcript_json.write_text(
                        json.dumps({"text": "今天我们聊聊AI对就业市场的影响。", "segments": []}),
                        encoding="utf-8",
                    )
                    run_manifest_json.write_text(
                        json.dumps({"task_id": "run-auto-fast", "mode": "fast", "selected_mode": "fast", "summary_source": "llm"}),
                        encoding="utf-8",
                    )
                    return FastRunResult(
                        task_id="run-auto-fast",
                        task_dir=task_dir,
                        video_path=video_path,
                        summary_md=summary_md,
                        timeline_json=timeline_json,
                        transcript_json=transcript_json,
                        run_manifest_json=run_manifest_json,
                        source_kind="bilibili_url",
                        summary_source="llm",
                    )

                def fail_fusion(*args, **kwargs):
                    raise AssertionError("fusion should not be called")

                auto_module._run_fast_pipeline = fake_run_fast
                auto_module._run_fusion_from_fast = fail_fusion

                result = auto_module.run_auto("https://example.com/video", output_root=root)
            finally:
                auto_module._run_fast_pipeline = original_run_fast
                auto_module._run_fusion_from_fast = original_run_fusion

            self.assertEqual(result.selected_mode, "fast")
            self.assertIn("verbal", result.selection_reason)
            manifest = json.loads(result.run_manifest_json.read_text(encoding="utf-8"))
            self.assertEqual(manifest["mode"], "auto")
            self.assertEqual(manifest["selected_mode"], "fast")
            self.assertEqual(manifest["auto_selection"]["decision"], "fast")

    def test_run_auto_upgrades_to_fusion_for_visual_video(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)

            import openclaw_video_summary.pipeline.auto as auto_module
            from openclaw_video_summary.pipeline.fast import FastRunResult
            from openclaw_video_summary.pipeline.fusion import FusionRunResult

            original_run_fast = auto_module._run_fast_pipeline
            original_run_fusion = auto_module._run_fusion_from_fast
            try:
                def fake_run_fast(input_value: str, *, output_root: Path | str, **_: object):
                    task_dir = Path(output_root) / "run-auto-fusion"
                    task_dir.mkdir(parents=True, exist_ok=True)
                    video_path = task_dir / "video.mp4"
                    summary_md = task_dir / "summary_zh.md"
                    timeline_json = task_dir / "timeline.json"
                    transcript_json = task_dir / "transcript.json"
                    run_manifest_json = task_dir / "summarize_manifest.json"
                    video_path.write_bytes(b"video")
                    summary_md.write_text("# Summary\n", encoding="utf-8")
                    timeline_json.write_text(
                        json.dumps(
                            {"timeline": [{"start": 0, "end": 60, "summary": "点击左边按钮并打开设置界面"}]}
                        ),
                        encoding="utf-8",
                    )
                    transcript_json.write_text(
                        json.dumps({"text": "现在点击左侧按钮，打开设置界面，再看图表变化。", "segments": []}),
                        encoding="utf-8",
                    )
                    run_manifest_json.write_text(
                        json.dumps({"task_id": "run-auto-fusion", "mode": "fast", "selected_mode": "fast", "summary_source": "llm"}),
                        encoding="utf-8",
                    )
                    return FastRunResult(
                        task_id="run-auto-fusion",
                        task_dir=task_dir,
                        video_path=video_path,
                        summary_md=summary_md,
                        timeline_json=timeline_json,
                        transcript_json=transcript_json,
                        run_manifest_json=run_manifest_json,
                        source_kind="youtube_url",
                        summary_source="llm",
                    )

                def fake_run_fusion(
                    fast_result,
                    *,
                    api_base: str,
                    api_key: str,
                    model: str,
                    chunk_sec: float,
                ):
                    evidence_json = fast_result.task_dir / "evidence.json"
                    fusion_report_md = fast_result.task_dir / "fusion_report.md"
                    evidence_json.write_text(json.dumps({"items": []}), encoding="utf-8")
                    fusion_report_md.write_text("# Fusion\n", encoding="utf-8")
                    manifest = {
                        "task_id": "run-auto-fusion",
                        "mode": "fusion",
                        "selected_mode": "fusion",
                        "summary_source": "llm_fusion",
                    }
                    fast_result.run_manifest_json.write_text(json.dumps(manifest), encoding="utf-8")
                    return FusionRunResult(
                        task_id=fast_result.task_id,
                        task_dir=fast_result.task_dir,
                        video_path=fast_result.video_path,
                        summary_md=fast_result.summary_md,
                        timeline_json=fast_result.timeline_json,
                        transcript_json=fast_result.transcript_json,
                        run_manifest_json=fast_result.run_manifest_json,
                        evidence_json=evidence_json,
                        fusion_report_md=fusion_report_md,
                        source_kind=fast_result.source_kind,
                    )

                auto_module._run_fast_pipeline = fake_run_fast
                auto_module._run_fusion_from_fast = fake_run_fusion

                result = auto_module.run_auto("https://example.com/video", output_root=root)
            finally:
                auto_module._run_fast_pipeline = original_run_fast
                auto_module._run_fusion_from_fast = original_run_fusion

            self.assertEqual(result.selected_mode, "fusion")
            self.assertTrue(result.evidence_json.exists())
            manifest = json.loads(result.run_manifest_json.read_text(encoding="utf-8"))
            self.assertEqual(manifest["mode"], "auto")
            self.assertEqual(manifest["selected_mode"], "fusion")
            self.assertEqual(manifest["auto_selection"]["decision"], "fusion")


if __name__ == "__main__":
    unittest.main()
