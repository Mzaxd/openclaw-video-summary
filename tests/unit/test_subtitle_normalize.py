from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from openclaw_video_summary.subtitle.normalize import subtitle_file_to_transcript


class SubtitleNormalizeTest(unittest.TestCase):
    def test_vtt_to_transcript_payload(self) -> None:
        with TemporaryDirectory() as td:
            path = Path(td) / "sample.vtt"
            path.write_text(
                "WEBVTT\n\n00:00:00.000 --> 00:00:01.200\n你好\n\n00:00:01.200 --> 00:00:02.400\n世界\n",
                encoding="utf-8",
            )
            payload = subtitle_file_to_transcript(path)
            self.assertEqual(len(payload.segments), 2)
            self.assertIn("你好", payload.text)

    def test_srt_to_transcript_payload(self) -> None:
        with TemporaryDirectory() as td:
            path = Path(td) / "sample.srt"
            path.write_text(
                "1\n00:00:00,000 --> 00:00:01,000\nhello\n\n2\n00:00:01,000 --> 00:00:02,000\nworld\n",
                encoding="utf-8",
            )
            payload = subtitle_file_to_transcript(path)
            self.assertEqual(len(payload.segments), 2)
            self.assertEqual(payload.segments[0]["start"], 0.0)

    def test_json3_to_transcript_payload(self) -> None:
        with TemporaryDirectory() as td:
            path = Path(td) / "sample.json3"
            path.write_text(
                json.dumps(
                    {
                        "events": [
                            {"tStartMs": 0, "dDurationMs": 1200, "segs": [{"utf8": "hello"}]},
                            {"tStartMs": 1200, "dDurationMs": 800, "segs": [{"utf8": "world"}]},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            payload = subtitle_file_to_transcript(path)
            self.assertEqual(len(payload.segments), 2)
            self.assertEqual(payload.text, "hello\nworld")


if __name__ == "__main__":
    unittest.main()
