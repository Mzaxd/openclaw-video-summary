from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from openclaw_video_summary.pipeline.task_layout import build_task_paths


class TaskLayoutTest(unittest.TestCase):
    def test_build_task_paths_returns_required_artifacts(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            paths = build_task_paths(root, "abc123")

            self.assertEqual(paths.task_dir, root / "abc123")
            self.assertEqual(paths.summary_md.name, "summary_zh.md")
            self.assertEqual(paths.timeline_json.name, "timeline.json")
            self.assertEqual(paths.transcript_json.name, "transcript.json")
            self.assertEqual(paths.run_manifest_json.name, "run_manifest.json")
            self.assertEqual(paths.video_path.name, "video.mp4")
            self.assertTrue(paths.task_dir.exists())


if __name__ == "__main__":
    unittest.main()
