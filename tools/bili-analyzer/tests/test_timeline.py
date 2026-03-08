from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bili_analyzer.timeline import build_timeline


class TestTimeline(unittest.TestCase):
    def test_build_timeline_merge_by_window(self) -> None:
        segments = [
            {"start": 0.0, "end": 10.0, "text": "A"},
            {"start": 15.0, "end": 20.0, "text": "B"},
            {"start": 130.0, "end": 140.0, "text": "C"},
        ]
        timeline = build_timeline(segments, window_sec=90.0)
        self.assertEqual(len(timeline), 2)
        self.assertEqual(timeline[0]["text"], "A B")
        self.assertEqual(timeline[1]["text"], "C")

    def test_build_timeline_ignore_empty_text(self) -> None:
        segments = [
            {"start": 0.0, "end": 1.0, "text": ""},
            {"start": 2.0, "end": 3.0, "text": "ok"},
        ]
        timeline = build_timeline(segments)
        self.assertEqual(len(timeline), 1)
        self.assertEqual(timeline[0]["text"], "ok")


if __name__ == "__main__":
    unittest.main()
