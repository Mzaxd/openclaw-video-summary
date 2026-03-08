from __future__ import annotations

import unittest

from openclaw_video_summary.vision.analyze import VisualEvidence, VisionAnalyzer


class VisionContractTest(unittest.TestCase):
    def test_visual_evidence_has_time_and_observation(self) -> None:
        item = VisualEvidence(
            start=0.0,
            end=5.0,
            observation="screen shows code",
            confidence="high",
        )
        self.assertEqual(item.observation, "screen shows code")
        self.assertEqual(item.confidence, "high")

    def test_vision_analyzer_requires_implementation(self) -> None:
        analyzer = VisionAnalyzer()
        with self.assertRaises(NotImplementedError):
            analyzer.analyze_video("/tmp/sample.mp4")


if __name__ == "__main__":
    unittest.main()
