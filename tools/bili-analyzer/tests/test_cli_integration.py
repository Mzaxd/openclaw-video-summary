from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


class TestCliIntegration(unittest.TestCase):
    def test_analyze_frames_json_summary_success(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            images_dir = Path(td) / "images"
            images_dir.mkdir(parents=True, exist_ok=True)

            img = Image.new("RGB", (16, 16), color=(255, 0, 0))
            img.save(images_dir / "frame_000001.jpg", format="JPEG")

            proc = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "bili_analyzer.cli",
                    "analyze-frames",
                    str(images_dir),
                    "--json-summary",
                ],
                capture_output=True,
                text=True,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["count"], 1)
            self.assertTrue(payload["index_file"].endswith("frames_index.json"))

    def test_prepare_invalid_similarity_failure(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            proc = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "bili_analyzer.cli",
                    "prepare",
                    "https://www.bilibili.com/video/BV1c1PszeEDk",
                    "-o",
                    td,
                    "--similarity",
                    "1.5",
                ],
                capture_output=True,
                text=True,
            )

            self.assertEqual(proc.returncode, 2)
            self.assertIn("similarity must be in [0,1]", proc.stderr)

    def test_transcribe_invalid_input_path_failure(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "bili_analyzer.cli",
                "transcribe",
                "./path/does/not/exist",
            ],
            capture_output=True,
            text=True,
        )

        self.assertEqual(proc.returncode, 2)
        self.assertIn("video input does not exist", proc.stderr)

    @unittest.skipUnless(
        os.environ.get("BILI_E2E") == "1",
        "Set BILI_E2E=1 to enable network e2e template",
    )
    def test_prepare_real_url_template(self) -> None:
        url = os.environ.get("BILI_TEST_URL", "https://www.bilibili.com/video/BV1c1PszeEDk")
        with tempfile.TemporaryDirectory() as td:
            proc = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "bili_analyzer.cli",
                    "prepare",
                    url,
                    "-o",
                    td,
                    "--fps",
                    "0.2",
                    "--similarity",
                    "0.8",
                    "--json-summary",
                ],
                capture_output=True,
                text=True,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertIn("frame_counts", payload)
            self.assertIn("timings_sec", payload)
            self.assertIsNotNone(payload.get("task_root"))


if __name__ == "__main__":
    unittest.main()
