from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest


class QualityPipelineTest(unittest.TestCase):
    def _write_manifest(self, task_dir: Path, payload: dict[str, object]) -> Path:
        path = task_dir / "run_manifest.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return path

    def test_run_quality_stays_in_quality_mode_when_enhancement_succeeds(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)

            import openclaw_video_summary.pipeline.quality as quality_module
            from openclaw_video_summary.pipeline.fusion import FusionRunResult

            original_run_fusion = quality_module._run_fusion_pipeline
            original_run_fast = quality_module._run_fast_pipeline
            original_enhancement = quality_module._run_quality_enhancement
            try:
                def fake_run_fusion(input_value: str, *, output_root: Path | str, **_: object):
                    task_dir = Path(output_root) / "run-quality"
                    task_dir.mkdir(parents=True, exist_ok=True)
                    video_path = task_dir / "video.mp4"
                    summary_md = task_dir / "summary_zh.md"
                    timeline_json = task_dir / "timeline.json"
                    transcript_json = task_dir / "transcript.json"
                    evidence_json = task_dir / "evidence.json"
                    fusion_report_md = task_dir / "fusion_report.md"
                    video_path.write_bytes(b"video")
                    summary_md.write_text("# Summary\n", encoding="utf-8")
                    timeline_json.write_text(json.dumps({"timeline": []}), encoding="utf-8")
                    transcript_json.write_text(json.dumps({"text": "hello", "segments": []}), encoding="utf-8")
                    evidence_json.write_text(json.dumps({"items": []}), encoding="utf-8")
                    fusion_report_md.write_text("# Fusion\n", encoding="utf-8")
                    run_manifest_json = self._write_manifest(
                        task_dir,
                        {
                            "task_id": "run-quality",
                            "mode": "fusion",
                            "selected_mode": "fusion",
                            "source_kind": "local_file",
                        },
                    )
                    return FusionRunResult(
                        task_id="run-quality",
                        task_dir=task_dir,
                        video_path=video_path,
                        summary_md=summary_md,
                        timeline_json=timeline_json,
                        transcript_json=transcript_json,
                        run_manifest_json=run_manifest_json,
                        evidence_json=evidence_json,
                        fusion_report_md=fusion_report_md,
                        source_kind="local_file",
                    )

                quality_module._run_fusion_pipeline = fake_run_fusion
                quality_module._run_fast_pipeline = lambda *args, **kwargs: None
                quality_module._run_quality_enhancement = lambda _result: {"score": "high"}

                result = quality_module.run_quality("https://example.com/video", output_root=root)
            finally:
                quality_module._run_fusion_pipeline = original_run_fusion
                quality_module._run_fast_pipeline = original_run_fast
                quality_module._run_quality_enhancement = original_enhancement

            self.assertEqual(result.selected_mode, "quality")
            self.assertIsNone(result.fallback)

            manifest = json.loads(result.run_manifest_json.read_text(encoding="utf-8"))
            self.assertEqual(manifest["mode"], "quality")
            self.assertEqual(manifest["selected_mode"], "quality")
            self.assertEqual(manifest["quality"]["score"], "high")

    def test_run_quality_downgrades_to_fusion_when_enhancement_fails(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)

            import openclaw_video_summary.pipeline.quality as quality_module
            from openclaw_video_summary.pipeline.fusion import FusionRunResult

            original_run_fusion = quality_module._run_fusion_pipeline
            original_enhancement = quality_module._run_quality_enhancement
            try:
                def fake_run_fusion(input_value: str, *, output_root: Path | str, **_: object):
                    task_dir = Path(output_root) / "run-fusion"
                    task_dir.mkdir(parents=True, exist_ok=True)
                    video_path = task_dir / "video.mp4"
                    summary_md = task_dir / "summary_zh.md"
                    timeline_json = task_dir / "timeline.json"
                    transcript_json = task_dir / "transcript.json"
                    evidence_json = task_dir / "evidence.json"
                    fusion_report_md = task_dir / "fusion_report.md"
                    video_path.write_bytes(b"video")
                    summary_md.write_text("# Summary\n", encoding="utf-8")
                    timeline_json.write_text(json.dumps({"timeline": []}), encoding="utf-8")
                    transcript_json.write_text(json.dumps({"text": "hello", "segments": []}), encoding="utf-8")
                    evidence_json.write_text(json.dumps({"items": []}), encoding="utf-8")
                    fusion_report_md.write_text("# Fusion\n", encoding="utf-8")
                    run_manifest_json = self._write_manifest(
                        task_dir,
                        {
                            "task_id": "run-fusion",
                            "mode": "fusion",
                            "selected_mode": "fusion",
                            "source_kind": "local_file",
                        },
                    )
                    return FusionRunResult(
                        task_id="run-fusion",
                        task_dir=task_dir,
                        video_path=video_path,
                        summary_md=summary_md,
                        timeline_json=timeline_json,
                        transcript_json=transcript_json,
                        run_manifest_json=run_manifest_json,
                        evidence_json=evidence_json,
                        fusion_report_md=fusion_report_md,
                        source_kind="local_file",
                    )

                quality_module._run_fusion_pipeline = fake_run_fusion

                def fail_quality(_result):
                    raise RuntimeError("quality backend unavailable")

                quality_module._run_quality_enhancement = fail_quality

                result = quality_module.run_quality("https://example.com/video", output_root=root)
            finally:
                quality_module._run_fusion_pipeline = original_run_fusion
                quality_module._run_quality_enhancement = original_enhancement

            self.assertEqual(result.selected_mode, "fusion")
            self.assertEqual(result.fallback["to"], "fusion")

            manifest = json.loads(result.run_manifest_json.read_text(encoding="utf-8"))
            self.assertEqual(manifest["mode"], "quality")
            self.assertEqual(manifest["selected_mode"], "fusion")
            self.assertEqual(manifest["fallback"]["reason"], "quality backend unavailable")

    def test_run_quality_downgrades_to_fast_when_fusion_fails(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)

            import openclaw_video_summary.pipeline.quality as quality_module
            from openclaw_video_summary.pipeline.fast import FastRunResult

            original_run_fusion = quality_module._run_fusion_pipeline
            original_run_fast = quality_module._run_fast_pipeline
            try:
                def fail_fusion(input_value: str, **_: object):
                    raise RuntimeError("fusion backend unavailable")

                def fake_run_fast(input_value: str, *, output_root: Path | str, **_: object):
                    task_dir = Path(output_root) / "run-fast"
                    task_dir.mkdir(parents=True, exist_ok=True)
                    video_path = task_dir / "video.mp4"
                    summary_md = task_dir / "summary_zh.md"
                    timeline_json = task_dir / "timeline.json"
                    transcript_json = task_dir / "transcript.json"
                    video_path.write_bytes(b"video")
                    summary_md.write_text("# Summary\n", encoding="utf-8")
                    timeline_json.write_text(json.dumps({"timeline": []}), encoding="utf-8")
                    transcript_json.write_text(json.dumps({"text": "hello", "segments": []}), encoding="utf-8")
                    run_manifest_json = self._write_manifest(
                        task_dir,
                        {
                            "task_id": "run-fast",
                            "mode": "fast",
                            "selected_mode": "fast",
                            "source_kind": "local_file",
                        },
                    )
                    return FastRunResult(
                        task_id="run-fast",
                        task_dir=task_dir,
                        video_path=video_path,
                        summary_md=summary_md,
                        timeline_json=timeline_json,
                        transcript_json=transcript_json,
                        run_manifest_json=run_manifest_json,
                        source_kind="local_file",
                    )

                quality_module._run_fusion_pipeline = fail_fusion
                quality_module._run_fast_pipeline = fake_run_fast

                result = quality_module.run_quality("https://example.com/video", output_root=root)
            finally:
                quality_module._run_fusion_pipeline = original_run_fusion
                quality_module._run_fast_pipeline = original_run_fast

            self.assertEqual(result.selected_mode, "fast")
            self.assertEqual(result.fallback["to"], "fast")
            self.assertEqual(result.fallback["reason"], "fusion backend unavailable")

            manifest = json.loads(result.run_manifest_json.read_text(encoding="utf-8"))
            self.assertEqual(manifest["mode"], "quality")
            self.assertEqual(manifest["selected_mode"], "fast")
            self.assertEqual(manifest["fallback"]["reason"], "fusion backend unavailable")


if __name__ == "__main__":
    unittest.main()
