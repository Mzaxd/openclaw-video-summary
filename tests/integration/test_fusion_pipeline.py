from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest


from openclaw_video_summary.vision.analyze import VisualEvidence


class FusionPipelineTest(unittest.TestCase):
    def test_run_fusion_writes_chunked_evidence_outputs(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)

            import openclaw_video_summary.pipeline.fusion as fusion_module

            original_run_fast = fusion_module._run_fast_pipeline
            original_split = fusion_module._split_video_chunks
            original_analyze = fusion_module._analyze_chunks
            original_rewrite = fusion_module._rewrite_summary_with_evidence
            try:
                def fake_run_fast(input_value: str, *, output_root: Path | str, **_: object):
                    task_dir = Path(output_root) / "run-1"
                    task_dir.mkdir(parents=True, exist_ok=True)
                    video_path = task_dir / "video.mp4"
                    summary_md = task_dir / "summary_zh.md"
                    timeline_json = task_dir / "timeline.json"
                    transcript_json = task_dir / "transcript.json"
                    run_manifest_json = task_dir / "summarize_manifest.json"
                    video_path.write_bytes(b"video")
                    summary_md.write_text("# Summary\n", encoding="utf-8")
                    timeline_json.write_text(json.dumps({"timeline": []}), encoding="utf-8")
                    transcript_json.write_text(
                        json.dumps(
                            {
                                "text": "hello",
                                "segments": [{"start": 0, "end": 3, "text": "hello world"}],
                            }
                        ),
                        encoding="utf-8",
                    )
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
                fusion_module._split_video_chunks = lambda *args, **kwargs: [
                    fusion_module.VideoChunk(
                        index=0,
                        start=0.0,
                        end=5.0,
                        path=Path(kwargs["chunks_dir"]) / "chunk_00.mp4",
                        asr_preview="00:00 hello world",
                    )
                ]
                fusion_module._analyze_chunks = lambda chunks, **kwargs: [
                    VisualEvidence(
                        start=chunks[0].start,
                        end=chunks[0].end,
                        observation="1) 画面内容摘要：主持人出镜\n2) 画面与口播一致性：高\n3) 关键画面证据：麦克风和字幕",
                        confidence="high",
                        metadata={
                            "chunk_index": chunks[0].index,
                            "chunk_path": str(chunks[0].path),
                            "asr_preview": chunks[0].asr_preview,
                        },
                    )
                ]
                fusion_module._rewrite_summary_with_evidence = lambda **kwargs: kwargs["summary_md"].write_text(
                    "# 融合总结\n\n## 摘要\n融合成功\n",
                    encoding="utf-8",
                )

                result = fusion_module.run_fusion(
                    "https://example.com/video",
                    output_root=root,
                    api_base="https://example.com/v1",
                    api_key="test-key",
                    chunk_sec=180.0,
                )
            finally:
                fusion_module._run_fast_pipeline = original_run_fast
                fusion_module._split_video_chunks = original_split
                fusion_module._analyze_chunks = original_analyze
                fusion_module._rewrite_summary_with_evidence = original_rewrite

            self.assertTrue(result.summary_md.exists())
            self.assertTrue(result.evidence_json.exists())
            self.assertTrue(result.fusion_report_md.exists())
            self.assertIsNone(result.fallback)
            self.assertIn("融合总结", result.summary_md.read_text(encoding="utf-8"))

            evidence = json.loads(result.evidence_json.read_text(encoding="utf-8"))
            self.assertEqual(evidence["items"][0]["chunk"], 0)
            self.assertEqual(evidence["items"][0]["metadata"]["asr_preview"], "00:00 hello world")

            manifest = json.loads(result.run_manifest_json.read_text(encoding="utf-8"))
            self.assertEqual(manifest["mode"], "fusion")
            self.assertEqual(manifest["selected_mode"], "fusion")
            self.assertEqual(manifest["chunk_sec"], 180.0)
            self.assertEqual(manifest["chunk_count"], 1)
            self.assertEqual(manifest["evidence_items"], 1)

    def test_run_fusion_downgrades_to_fast_when_chunk_analysis_fails(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)

            import openclaw_video_summary.pipeline.fusion as fusion_module

            original_run_fast = fusion_module._run_fast_pipeline
            original_split = fusion_module._split_video_chunks
            original_analyze = fusion_module._analyze_chunks
            original_rewrite = fusion_module._rewrite_summary_with_evidence
            try:
                def fake_run_fast(input_value: str, *, output_root: Path | str, **_: object):
                    task_dir = Path(output_root) / "run-2"
                    task_dir.mkdir(parents=True, exist_ok=True)
                    video_path = task_dir / "video.mp4"
                    summary_md = task_dir / "summary_zh.md"
                    timeline_json = task_dir / "timeline.json"
                    transcript_json = task_dir / "transcript.json"
                    run_manifest_json = task_dir / "summarize_manifest.json"
                    video_path.write_bytes(b"video")
                    summary_md.write_text("# Summary\n", encoding="utf-8")
                    timeline_json.write_text(json.dumps({"timeline": []}), encoding="utf-8")
                    transcript_json.write_text(
                        json.dumps({"text": "hello", "segments": []}),
                        encoding="utf-8",
                    )
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
                fusion_module._split_video_chunks = lambda *args, **kwargs: [
                    fusion_module.VideoChunk(
                        index=0,
                        start=0.0,
                        end=5.0,
                        path=Path(kwargs["chunks_dir"]) / "chunk_00.mp4",
                        asr_preview="",
                    )
                ]

                def fail_analysis(*args, **kwargs):
                    raise RuntimeError("chunk video analysis unavailable")

                fusion_module._analyze_chunks = fail_analysis
                fusion_module._rewrite_summary_with_evidence = lambda **kwargs: None

                result = fusion_module.run_fusion(
                    "https://example.com/video",
                    output_root=root,
                    api_base="https://example.com/v1",
                    api_key="test-key",
                    chunk_sec=180.0,
                )
            finally:
                fusion_module._run_fast_pipeline = original_run_fast
                fusion_module._split_video_chunks = original_split
                fusion_module._analyze_chunks = original_analyze
                fusion_module._rewrite_summary_with_evidence = original_rewrite

            self.assertTrue(result.summary_md.exists())
            self.assertFalse(result.evidence_json.exists())
            self.assertFalse(result.fusion_report_md.exists())
            self.assertEqual(result.fallback["to"], "fast")

            manifest = json.loads(result.run_manifest_json.read_text(encoding="utf-8"))
            self.assertEqual(manifest["mode"], "fusion")
            self.assertEqual(manifest["selected_mode"], "fast")
            self.assertEqual(manifest["chunk_sec"], 180.0)
            self.assertEqual(manifest["fallback"]["reason"], "chunk video analysis unavailable")


if __name__ == "__main__":
    unittest.main()
