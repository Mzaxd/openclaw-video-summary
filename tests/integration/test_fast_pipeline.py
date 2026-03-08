from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest


from openclaw_video_summary.asr.transcribe import TranscriptPayload
from openclaw_video_summary.pipeline.fast import run_fast


class FastPipelineTest(unittest.TestCase):
    def test_run_fast_returns_base_artifacts(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            sample = root / "sample.mp4"
            sample.write_bytes(b"fake-video")

            import openclaw_video_summary.pipeline.fast as fast_module

            original_task_id = fast_module._build_task_id
            original_transcribe = fast_module._transcribe_video
            original_request_summary = fast_module._request_summary_text
            try:
                fast_module._build_task_id = lambda _value: "run-1"
                fast_module._transcribe_video = lambda *, video_path, transcript_path: TranscriptPayload(
                    text="hello world",
                    segments=[
                        {"start": 0.0, "end": 5.0, "text": "hello"},
                        {"start": 5.0, "end": 10.0, "text": "world"},
                    ],
                )
                fast_module._request_summary_text = lambda **_kwargs: "# 总结\n\n- hello world\n"

                result = run_fast(str(sample), output_root=root)
            finally:
                fast_module._build_task_id = original_task_id
                fast_module._transcribe_video = original_transcribe
                fast_module._request_summary_text = original_request_summary

            self.assertEqual(result.task_id, "run-1")
            self.assertTrue(result.summary_md.exists())
            self.assertTrue(result.timeline_json.exists())
            self.assertTrue(result.transcript_json.exists())
            self.assertTrue(result.run_manifest_json.exists())
            self.assertTrue(result.video_path.exists())
            self.assertEqual(result.source_kind, "local_file")

            manifest = json.loads(result.run_manifest_json.read_text(encoding="utf-8"))
            self.assertEqual(manifest["task_id"], "run-1")
            self.assertEqual(manifest["source_kind"], "local_file")
            self.assertEqual(manifest["mode"], "fast")

            timeline = json.loads(result.timeline_json.read_text(encoding="utf-8"))
            self.assertEqual(timeline["timeline"][0]["summary"], "hello world")

            transcript = json.loads(result.transcript_json.read_text(encoding="utf-8"))
            self.assertEqual(transcript["text"], "hello world")


if __name__ == "__main__":
    unittest.main()
