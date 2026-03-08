import unittest

from openclaw_video_summary.timeline.build import build_timeline


class TimelineBuildTest(unittest.TestCase):
    def test_build_timeline_groups_segments_into_windows(self) -> None:
        segments = [
            {"start": 0.0, "end": 10.0, "text": "a"},
            {"start": 15.0, "end": 20.0, "text": "b"},
        ]

        timeline = build_timeline(segments, window_sec=30)

        self.assertEqual(len(timeline), 1)
        self.assertEqual(timeline[0]["start"], 0.0)
        self.assertEqual(timeline[0]["end"], 20.0)
        self.assertEqual(timeline[0]["summary"], "a b")


if __name__ == "__main__":
    unittest.main()
