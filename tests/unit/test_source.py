from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from openclaw_video_summary.ingest.source import detect_source_kind


class SourceDetectionTest(unittest.TestCase):
    def test_detects_youtube_url(self) -> None:
        self.assertEqual(detect_source_kind("https://www.youtube.com/watch?v=abc"), "youtube")

    def test_detects_bilibili_url(self) -> None:
        self.assertEqual(detect_source_kind("https://www.bilibili.com/video/BV1xxxx"), "bilibili")

    def test_detects_local_path(self) -> None:
        with TemporaryDirectory() as td:
            video = Path(td) / "clip.mp4"
            video.write_bytes(b"test")
            self.assertEqual(detect_source_kind(str(video)), "local_file")

    def test_rejects_unknown_input(self) -> None:
        with self.assertRaises(ValueError):
            detect_source_kind("not-a-supported-input")


if __name__ == "__main__":
    unittest.main()
