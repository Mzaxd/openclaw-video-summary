from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from openclaw_video_summary.ingest.download import normalize_input_to_video


class DownloadContractTest(unittest.TestCase):
    def test_local_input_is_materialized_as_video_mp4(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            src = root / "source.mp4"
            src.write_bytes(b"video")
            out_dir = root / "run"

            result = normalize_input_to_video(str(src), out_dir)

            self.assertEqual(result.video_path.name, "video.mp4")
            self.assertTrue(result.video_path.exists())
            self.assertEqual(result.video_path.read_bytes(), b"video")
            self.assertEqual(result.source_kind, "local_file")


if __name__ == "__main__":
    unittest.main()
