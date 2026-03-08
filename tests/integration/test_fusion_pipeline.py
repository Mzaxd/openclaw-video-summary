from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest


from openclaw_video_summary.vision.analyze import VisualEvidence


class FusionPipelineTest(unittest.TestCase):
    def test_run_fusion_writes_evidence_outputs(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)

            import openclaw_video_summary.pipeline.fusion as fusion_module

            original_run_fast = fusion_module._run_fast_pipeline
            original_analyze_video = fusion_module._analyze_video
            try:
                def fake_run_fast(input_value: str, *, output_root: Path | str, **_: object):
                    task_dir = Path(output_root) / "run-1"
                    task_dir.mkdir(parents=True, exist_ok=True)
                    video_path = task_dir / "video.mp4"
                    summary_md = task_dir / "summary_zh.md"
                    timeline_json = task_dir / "timeline.json"
                    transcript_json = task_dir / "transcript.json"
                    run_manifest_json = task_dir / "run_manifest.json"
                    video_path.write_bytes(b"video")
                    summary_md.write_text("# Summary\n", encoding="utf-8")
                    timeline_json.write_text(json.dumps({"timeline": []}), encoding="utf-8")
                    transcript_json.write_text(json.dumps({"text": "hello", "segments": []}), encoding="utf-8")
                    run_manifest_json.write_text(
                        json.dumps({"task_id": "run-1", "mode": "fast", "source_kind": "local_file"}, ensure_ascii=False),
                        encoding="utf-8",
                    )
                    return fusion_module.FastRunResult(
                        task_id="run-1",
                        task_dir=task_dir,
                        video_path=video_path,
                        summary_md=summary_md,
                        timeline_json=timeline_json,
                        transcript_json=transcript_json,
                        run_manifest_json=run_manifest_json,
                        source_kind="local_file",
                    )

                fusion_module._run_fast_pipeline = fake_run_fast
                fusion_module._analyze_video = lambda _path: [
                    VisualEvidence(start=0.0, end=5.0, observation="screen shows slides", confidence="high")
                ]

                result = fusion_module.run_fusion("https://example.com/video", output_root=root)
            finally:
                fusion_module._run_fast_pipeline = original_run_fast
                fusion_module._analyze_video = original_analyze_video

            self.assertTrue(result.summary_md.exists())
            self.assertTrue(result.evidence_json.exists())
            self.assertTrue(result.fusion_report_md.exists())
            self.assertIsNone(result.fallback)

            evidence = json.loads(result.evidence_json.read_text(encoding="utf-8"))
            self.assertEqual(evidence["items"][0]["observation"], "screen shows slides")

            manifest = json.loads(result.run_manifest_json.read_text(encoding="utf-8"))
            self.assertEqual(manifest["mode"], "fusion")
            self.assertEqual(manifest["selected_mode"], "fusion")
            self.assertEqual(manifest["evidence_items"], 1)

    def test_run_fusion_downgrades_to_fast_when_vision_fails(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)

            import openclaw_video_summary.pipeline.fusion as fusion_module

            original_run_fast = fusion_module._run_fast_pipeline
            original_analyze_video = fusion_module._analyze_video
            try:
                def fake_run_fast(input_value: str, *, output_root: Path | str, **_: object):
                    task_dir = Path(output_root) / "run-2"
                    task_dir.mkdir(parents=True, exist_ok=True)
                    video_path = task_dir / "video.mp4"
                    summary_md = task_dir / "summary_zh.md"
                    timeline_json = task_dir / "timeline.json"
                    transcript_json = task_dir / "transcript.json"
                    run_manifest_json = task_dir / "run_manifest.json"
                    video_path.write_bytes(b"video")
                    summary_md.write_text("# Summary\n", encoding="utf-8")
                    timeline_json.write_text(json.dumps({"timeline": []}), encoding="utf-8")
                    transcript_json.write_text(json.dumps({"text": "hello", "segments": []}), encoding="utf-8")
                    run_manifest_json.write_text(
                        json.dumps({"task_id": "run-2", "mode": "fast", "source_kind": "local_file"}, ensure_ascii=False),
                        encoding="utf-8",
                    )
                    return fusion_module.FastRunResult(
                        task_id="run-2",
                        task_dir=task_dir,
                        video_path=video_path,
                        summary_md=summary_md,
                        timeline_json=timeline_json,
                        transcript_json=transcript_json,
                        run_manifest_json=run_manifest_json,
                        source_kind="local_file",
                    )

                fusion_module._run_fast_pipeline = fake_run_fast

                def fail_analysis(_path: Path):
                    raise RuntimeError("vision backend unavailable")

                fusion_module._analyze_video = fail_analysis

                result = fusion_module.run_fusion("https://example.com/video", output_root=root)
            finally:
                fusion_module._run_fast_pipeline = original_run_fast
                fusion_module._analyze_video = original_analyze_video

            self.assertTrue(result.summary_md.exists())
            self.assertFalse(result.evidence_json.exists())
            self.assertFalse(result.fusion_report_md.exists())
            self.assertEqual(result.fallback["to"], "fast")

            manifest = json.loads(result.run_manifest_json.read_text(encoding="utf-8"))
            self.assertEqual(manifest["mode"], "fusion")
            self.assertEqual(manifest["selected_mode"], "fast")
            self.assertEqual(manifest["fallback"]["reason"], "vision backend unavailable")


if __name__ == "__main__":
    unittest.main()
