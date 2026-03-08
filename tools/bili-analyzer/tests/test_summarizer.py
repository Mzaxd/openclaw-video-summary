from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bili_analyzer.summarizer import summarize_video


class TestSummarizer(unittest.TestCase):
    def _prepare_transcript(self, root: Path) -> Path:
        transcript_path = root / "transcript.json"
        payload = {
            "text": "Hello world. This is an English talk about product strategy.",
            "segments": [
                {"start": 0.0, "end": 10.0, "text": "Hello world."},
                {"start": 12.0, "end": 35.0, "text": "This is an English talk about product strategy."},
            ],
        }
        transcript_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return transcript_path

    @patch("bili_analyzer.summarizer.analyze_frames_dir")
    @patch("bili_analyzer.summarizer._call_llm_summary")
    @patch("bili_analyzer.summarizer.transcribe_video")
    @patch("bili_analyzer.summarizer.prepare_video")
    def test_fusion_fallback_to_fast_when_first_llm_call_fails(
        self,
        mock_prepare,
        mock_transcribe,
        mock_call_llm,
        mock_analyze_frames,
    ) -> None:
        with tempfile.TemporaryDirectory() as td:
            task_root = Path(td) / "bili-test"
            images_dir = task_root / "images"
            images_dir.mkdir(parents=True, exist_ok=True)
            transcript_path = self._prepare_transcript(task_root)

            mock_prepare.return_value = {"task_root": str(task_root)}
            mock_transcribe.return_value = {"transcript_file": str(transcript_path)}
            mock_analyze_frames.return_value = {"count": 10, "preview": ["a.jpg", "b.jpg"]}
            mock_call_llm.side_effect = [Exception("fusion failed"), "# 中文总结\n\n内容"]

            result = summarize_video(
                url="https://www.bilibili.com/video/BV1test",
                output=td,
                mode="fusion",
                api_base="https://example.com",
                api_key="test",
            )

            self.assertEqual(result["summary_source"], "llm")
            self.assertIsNotNone(result["fallback"])
            self.assertEqual(result["fallback"]["from"], "fusion")
            self.assertTrue((task_root / "summary_zh.md").exists())
            self.assertTrue((task_root / "timeline.json").exists())

    @patch("bili_analyzer.summarizer._call_llm_summary", side_effect=Exception("llm down"))
    @patch("bili_analyzer.summarizer.transcribe_video")
    @patch("bili_analyzer.summarizer.prepare_video")
    def test_local_fallback_when_llm_unavailable(self, mock_prepare, mock_transcribe, _mock_llm) -> None:
        with tempfile.TemporaryDirectory() as td:
            task_root = Path(td) / "bili-test"
            task_root.mkdir(parents=True, exist_ok=True)
            transcript_path = self._prepare_transcript(task_root)

            mock_prepare.return_value = {"task_root": str(task_root)}
            mock_transcribe.return_value = {"transcript_file": str(transcript_path)}

            result = summarize_video(
                url="https://www.bilibili.com/video/BV1test",
                output=td,
                mode="fast",
                api_base="https://example.com",
                api_key="test",
            )

            self.assertEqual(result["summary_source"], "local_fallback")
            summary_text = (task_root / "summary_zh.md").read_text(encoding="utf-8")
            self.assertIn("视频中文总结（降级结果）", summary_text)


if __name__ == "__main__":
    unittest.main()
