from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from openclaw_video_summary.pipeline.fast import run_fast


class FastPipelineSubtitleFirstTest(unittest.TestCase):
    def test_run_fast_short_circuits_download_and_asr_on_subtitle_hit(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            subtitle = root / "subtitle.vtt"
            subtitle.write_text(
                "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nhello subtitle\n",
                encoding="utf-8",
            )

            import openclaw_video_summary.pipeline.fast as fast_module

            original_task_id = fast_module._build_task_id
            original_probe = fast_module.probe_subtitle
            original_download = fast_module.normalize_input_to_video
            original_transcribe = fast_module._transcribe_video
            original_request_summary = fast_module._request_summary_text
            try:
                fast_module._build_task_id = lambda _value: "run-subtitle"
                fast_module.probe_subtitle = lambda *_args, **_kwargs: {
                    "status": "success",
                    "provider": "yt-dlp",
                    "language": "en",
                    "subtitle_path": str(subtitle),
                    "duration_sec": 0.1,
                    "reason": "",
                }

                def fail_download(*_args, **_kwargs):
                    raise AssertionError("download should not be called when subtitle is available")

                def fail_transcribe(*_args, **_kwargs):
                    raise AssertionError("asr should not be called when subtitle is available")

                fast_module.normalize_input_to_video = fail_download
                fast_module._transcribe_video = fail_transcribe
                fast_module._request_summary_text = lambda **_kwargs: "# 总结\n\n- ok\n"

                result = run_fast("https://www.youtube.com/watch?v=abc", output_root=root)
            finally:
                fast_module._build_task_id = original_task_id
                fast_module.probe_subtitle = original_probe
                fast_module.normalize_input_to_video = original_download
                fast_module._transcribe_video = original_transcribe
                fast_module._request_summary_text = original_request_summary

            manifest = json.loads(result.run_manifest_json.read_text(encoding="utf-8"))
            self.assertEqual(manifest["transcript_source"], "subtitle")
            self.assertTrue(manifest["subtitle_probe"]["success"])
            self.assertEqual(manifest["source_kind"], "youtube")
            self.assertEqual(manifest["transcribe"]["engine"], "subtitle")


if __name__ == "__main__":
    unittest.main()
