import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


class CliIntegrationTest(unittest.TestCase):
    def test_cli_exposes_summarize_command(self) -> None:
        proc = subprocess.run(
            [sys.executable, "-m", "openclaw_video_summary.interfaces.cli", "--help"],
            capture_output=True,
            text=True,
        )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("summarize", proc.stdout)

    def test_cli_dispatches_selected_mode_with_json_summary(self) -> None:
        import openclaw_video_summary.interfaces.cli as cli_module

        original_fast = cli_module.run_fast
        original_fusion = cli_module.run_fusion
        original_quality = cli_module.run_quality
        try:
            def fail_fast(*args, **kwargs):
                raise AssertionError("fast should not be called")

            def fail_fusion(*args, **kwargs):
                raise AssertionError("fusion should not be called")

            def fake_quality(input_value: str, **kwargs):
                with tempfile.TemporaryDirectory() as td:
                    task_dir = Path(td) / "run-quality"
                    task_dir.mkdir(parents=True, exist_ok=True)
                    summary_md = task_dir / "summary_zh.md"
                    timeline_json = task_dir / "timeline.json"
                    transcript_json = task_dir / "transcript.json"
                    run_manifest_json = task_dir / "run_manifest.json"
                    video_path = task_dir / "video.mp4"
                    for path in (summary_md, timeline_json, transcript_json, run_manifest_json, video_path):
                        path.write_text("{}", encoding="utf-8")

                    from openclaw_video_summary.pipeline.quality import QualityRunResult

                    return QualityRunResult(
                        task_id="run-quality",
                        task_dir=task_dir,
                        video_path=video_path,
                        summary_md=summary_md,
                        timeline_json=timeline_json,
                        transcript_json=transcript_json,
                        run_manifest_json=run_manifest_json,
                        selected_mode="quality",
                        source_kind="local_file",
                        fallback=None,
                    )

            cli_module.run_fast = fail_fast
            cli_module.run_fusion = fail_fusion
            cli_module.run_quality = fake_quality

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = cli_module.main(
                    [
                        "summarize",
                        "/tmp/sample.mp4",
                        "--mode",
                        "quality",
                        "-o",
                        "/tmp/out",
                        "--json-summary",
                    ]
                )
        finally:
            cli_module.run_fast = original_fast
            cli_module.run_fusion = original_fusion
            cli_module.run_quality = original_quality

        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["mode"], "quality")
        self.assertEqual(payload["selected_mode"], "quality")
        self.assertEqual(payload["source_kind"], "local_file")


if __name__ == "__main__":
    unittest.main()
