import unittest

from openclaw_video_summary.summary.prompts import build_summary_messages


class SummaryClientTest(unittest.TestCase):
    def test_summary_prompt_requires_chinese_output(self) -> None:
        messages = build_summary_messages(
            "english transcript",
            [{"start": 0, "end": 10, "summary": "x"}],
            None,
        )

        self.assertIn("中文", messages[0]["content"])


if __name__ == "__main__":
    unittest.main()
