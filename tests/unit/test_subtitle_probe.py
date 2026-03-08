from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from openclaw_video_summary.subtitle.probe import probe_subtitle


class SubtitleProbeTest(unittest.TestCase):
    @patch("openclaw_video_summary.subtitle.probe.shutil.which", return_value="/usr/local/bin/yt-dlp")
    @patch("openclaw_video_summary.subtitle.probe._probe_with_cookies")
    def test_probe_success_returns_metadata(self, mock_probe, _mock_which) -> None:
        mock_probe.return_value = {
            "status": "success",
            "provider": "yt-dlp",
            "language": "zh",
            "subtitle_path": "/tmp/sub.vtt",
            "reason": "",
        }
        result = probe_subtitle("https://www.youtube.com/watch?v=abc", timeout_sec=5.0)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["provider"], "yt-dlp")
        self.assertEqual(result["language"], "zh")

    @patch("openclaw_video_summary.subtitle.probe.shutil.which", return_value="/usr/local/bin/yt-dlp")
    @patch("openclaw_video_summary.subtitle.probe._probe_with_cookies")
    def test_timeout_result_is_propagated(self, mock_probe, _mock_which) -> None:
        mock_probe.return_value = {
            "status": "timeout",
            "reason": "subtitle probe timed out after 5.0s",
        }
        result = probe_subtitle("https://www.bilibili.com/video/BV1x", timeout_sec=5.0)
        self.assertEqual(result["status"], "timeout")

    @patch("openclaw_video_summary.subtitle.probe.shutil.which", return_value="/usr/local/bin/yt-dlp")
    @patch("openclaw_video_summary.subtitle.probe._probe_without_cookies")
    @patch("openclaw_video_summary.subtitle.probe._probe_with_cookies")
    def test_cookie_failure_retries_without_cookie(self, with_cookie, without_cookie, _mock_which) -> None:
        with_cookie.return_value = {"status": "error", "reason": "cookies_from_browser_failed"}
        without_cookie.return_value = {"status": "miss", "reason": "no_subtitle_found"}
        result = probe_subtitle("https://www.youtube.com/watch?v=abc", timeout_sec=5.0, cookies_from_browser=True)
        self.assertEqual(result["status"], "miss")
        without_cookie.assert_called_once()

    def test_local_file_skips_probe(self) -> None:
        with TemporaryDirectory() as td:
            sample = Path(td) / "video.mp4"
            sample.write_bytes(b"x")
            result = probe_subtitle(str(sample))
            self.assertEqual(result["status"], "miss")
            self.assertEqual(result["reason"], "source_kind_not_supported")


if __name__ == "__main__":
    unittest.main()
