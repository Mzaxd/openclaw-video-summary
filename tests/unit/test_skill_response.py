from __future__ import annotations

import unittest

from openclaw_video_summary.interfaces.skill_response import format_skill_response


class SkillResponseTest(unittest.TestCase):
    def test_skill_response_includes_summary_timeline_and_evidence(self) -> None:
        text = format_skill_response(
            summary_md="# 总结\n\n这是中文总结。",
            timeline_items=[
                {"start": 0, "end": 10, "summary": "intro"},
                {"start": 10, "end": 20, "summary": "demo"},
            ],
            evidence_items=[
                {"observation": "slides visible"},
                {"observation": "terminal output shown"},
            ],
            task_dir="/tmp/run-1",
            artifact_paths={
                "summary_zh.md": "/tmp/run-1/summary_zh.md",
                "timeline.json": "/tmp/run-1/timeline.json",
            },
        )
        self.assertIn("## 中文总结", text)
        self.assertIn("这是中文总结。", text)
        self.assertIn("## 时间线", text)
        self.assertIn("0s - 10s", text)
        self.assertIn("## 关键证据", text)
        self.assertIn("slides visible", text)
        self.assertIn("## 产物路径", text)
        self.assertIn("/tmp/run-1", text)


if __name__ == "__main__":
    unittest.main()
