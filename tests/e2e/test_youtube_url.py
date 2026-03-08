import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


@unittest.skipUnless(os.environ.get("OCVS_E2E") == "1", "Set OCVS_E2E=1 to enable source E2E tests")
class YouTubeUrlE2ETest(unittest.TestCase):
    def test_youtube_url_fast_mode_template(self) -> None:
        url = os.environ.get("OCVS_YOUTUBE_URL")
        api_base = os.environ.get("OCVS_API_BASE")
        api_key = os.environ.get("OCVS_API_KEY")

        self.assertTrue(url, "Set OCVS_YOUTUBE_URL to enable the YouTube E2E template")
        self.assertTrue(api_base, "Set OCVS_API_BASE to enable the YouTube E2E template")
        self.assertTrue(api_key, "Set OCVS_API_KEY to enable the YouTube E2E template")

        with tempfile.TemporaryDirectory() as td:
            proc = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "openclaw_video_summary.interfaces.cli",
                    "summarize",
                    url,
                    "--mode",
                    "fast",
                    "--output-root",
                    td,
                    "--api-base",
                    api_base,
                    "--api-key",
                    api_key,
                    "--json-summary",
                ],
                capture_output=True,
                text=True,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["mode"], "fast")

            task_dir = Path(payload["task_dir"])
            self.assertTrue(task_dir.exists())
            self.assertTrue(Path(payload["summary_md"]).exists())
            self.assertTrue(Path(payload["timeline_json"]).exists())
            self.assertTrue(Path(payload["transcript_json"]).exists())
            self.assertTrue(Path(payload["run_manifest_json"]).exists())


if __name__ == "__main__":
    unittest.main()
