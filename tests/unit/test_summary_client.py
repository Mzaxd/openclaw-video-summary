import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from openclaw_video_summary.summary.prompts import (
    build_summary_messages,
    normalize_summary_markdown,
    resolve_summary_template_path,
)


class SummaryClientTest(unittest.TestCase):
    def test_summary_prompt_requires_chinese_output(self) -> None:
        messages = build_summary_messages(
            "english transcript",
            [{"start": 0, "end": 10, "summary": "x"}],
            None,
        )

        self.assertIn("中文", messages[1]["content"])
        self.assertIn("亮点", messages[1]["content"])
        self.assertIn("关键洞察", messages[1]["content"])

    def test_normalize_summary_markdown_strips_fence(self) -> None:
        content = "```markdown\n# 标题\n\n内容\n```"
        self.assertEqual(normalize_summary_markdown(content), "# 标题\n\n内容\n")

    def test_build_summary_messages_can_use_custom_template_file(self) -> None:
        with TemporaryDirectory() as td:
            template_path = Path(td) / "summary_prompt.md"
            template_path.write_text(
                "自定义模板\n视觉={{visual_context}}\n时间线={{timeline_brief}}\n正文={{transcript_text}}\n",
                encoding="utf-8",
            )
            original = os.environ.get("OCVS_SUMMARY_TEMPLATE_FILE")
            try:
                os.environ["OCVS_SUMMARY_TEMPLATE_FILE"] = str(template_path)
                messages = build_summary_messages(
                    "hello transcript",
                    [{"start": 0, "end": 10, "summary": "段落摘要"}],
                    {"mode": "fusion"},
                )
            finally:
                if original is None:
                    os.environ.pop("OCVS_SUMMARY_TEMPLATE_FILE", None)
                else:
                    os.environ["OCVS_SUMMARY_TEMPLATE_FILE"] = original

            self.assertIn("自定义模板", messages[1]["content"])
            self.assertIn("hello transcript", messages[1]["content"])
            self.assertIn("段落摘要", messages[1]["content"])

    def test_resolve_summary_template_path_defaults_to_repo_local_when_present(self) -> None:
        path = resolve_summary_template_path()
        self.assertTrue(path.name in {"summary_prompt.local.md", "summary_prompt.md", "summary_prompt.default.md"})


if __name__ == "__main__":
    unittest.main()
