import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import types
import unittest

import openclaw_video_summary.asr.transcribe as transcribe_module
from openclaw_video_summary.asr.transcribe import TranscriptPayload, resolve_transcribe_runtime


class TranscribeContractTest(unittest.TestCase):
    def test_transcript_payload_has_text_and_segments(self) -> None:
        payload = TranscriptPayload(
            text="hello",
            segments=[{"start": 0.0, "end": 1.0, "text": "hello"}],
        )

        self.assertEqual(payload.text, "hello")
        self.assertEqual(payload.segments[0]["text"], "hello")

    def test_resolve_transcribe_runtime_includes_profile_metadata(self) -> None:
        runtime = resolve_transcribe_runtime(
            platform_name="darwin",
            machine="arm64",
            platform_profile="auto",
            device="auto",
            compute_type="int8",
            env={},
        )

        self.assertEqual(runtime["device"], "mps")
        self.assertEqual(runtime["compute_type"], "int8_float16")
        self.assertEqual(runtime["profile"], "apple_silicon")

    def test_transcribe_apple_silicon_uses_mlx_backend_when_available(self) -> None:
        with TemporaryDirectory() as td:
            out_dir = Path(td) / "out"
            out_dir.mkdir(parents=True, exist_ok=True)
            video_path = Path(td) / "video.mp4"
            video_path.write_bytes(b"video")

            fake_core = types.ModuleType("bili_analyzer.core")
            fake_core.transcribe_video = lambda **_kwargs: (_ for _ in ()).throw(AssertionError("should not call faster-whisper"))
            fake_pkg = types.ModuleType("bili_analyzer")
            fake_pkg.core = fake_core
            old_pkg = sys.modules.get("bili_analyzer")
            old_core = sys.modules.get("bili_analyzer.core")
            sys.modules["bili_analyzer"] = fake_pkg
            sys.modules["bili_analyzer.core"] = fake_core

            original_ensure = transcribe_module._ensure_bili_analyzer_import
            original_runtime = transcribe_module.resolve_transcribe_runtime
            original_mlx = transcribe_module._transcribe_with_mlx_backend
            try:
                transcribe_module._ensure_bili_analyzer_import = lambda: None
                transcribe_module.resolve_transcribe_runtime = lambda **_kwargs: {
                    "profile": "apple_silicon",
                    "device": "mps",
                    "compute_type": "int8_float16",
                    "reason": "apple silicon",
                }
                transcribe_module._transcribe_with_mlx_backend = lambda **_kwargs: (
                    TranscriptPayload(
                        text="mlx hello",
                        segments=[{"start": 0.0, "end": 1.0, "text": "mlx hello"}],
                    ),
                    {
                        "transcript_file": str(out_dir / "transcript.json"),
                        "runtime_profile": {
                            "profile": "apple_silicon",
                            "device": "mps",
                            "compute_type": "int8_float16",
                            "reason": "apple silicon",
                        },
                        "engine": "mlx-whisper",
                    },
                )
                (out_dir / "transcript.json").write_text(
                    json.dumps({"text": "mlx hello", "segments": [{"start": 0.0, "end": 1.0, "text": "mlx hello"}]}),
                    encoding="utf-8",
                )
                payload, result = transcribe_module.transcribe_with_backend(
                    input_path=video_path,
                    output_dir=out_dir,
                    platform_profile="apple_silicon",
                )
            finally:
                transcribe_module._ensure_bili_analyzer_import = original_ensure
                transcribe_module.resolve_transcribe_runtime = original_runtime
                transcribe_module._transcribe_with_mlx_backend = original_mlx
                if old_pkg is None:
                    sys.modules.pop("bili_analyzer", None)
                else:
                    sys.modules["bili_analyzer"] = old_pkg
                if old_core is None:
                    sys.modules.pop("bili_analyzer.core", None)
                else:
                    sys.modules["bili_analyzer.core"] = old_core

            self.assertEqual(payload.text, "mlx hello")
            self.assertEqual(result["engine"], "mlx-whisper")
            self.assertEqual(result["runtime_profile"]["device"], "mps")

    def test_transcribe_apple_silicon_falls_back_to_cpu_when_mlx_unavailable(self) -> None:
        with TemporaryDirectory() as td:
            out_dir = Path(td) / "out"
            out_dir.mkdir(parents=True, exist_ok=True)
            video_path = Path(td) / "video.mp4"
            video_path.write_bytes(b"video")
            transcript_path = out_dir / "transcript.json"
            transcript_path.write_text(
                json.dumps({"text": "cpu hello", "segments": [{"start": 0.0, "end": 1.0, "text": "cpu hello"}]}),
                encoding="utf-8",
            )

            calls: dict[str, str] = {}

            def fake_transcribe_video(**kwargs):
                calls["device"] = kwargs["device"]
                calls["compute_type"] = kwargs["compute_type"]
                return {
                    "transcript_file": str(transcript_path),
                    "engine": "faster-whisper",
                }

            fake_core = types.ModuleType("bili_analyzer.core")
            fake_core.transcribe_video = fake_transcribe_video
            fake_pkg = types.ModuleType("bili_analyzer")
            fake_pkg.core = fake_core
            old_pkg = sys.modules.get("bili_analyzer")
            old_core = sys.modules.get("bili_analyzer.core")
            sys.modules["bili_analyzer"] = fake_pkg
            sys.modules["bili_analyzer.core"] = fake_core

            original_ensure = transcribe_module._ensure_bili_analyzer_import
            original_runtime = transcribe_module.resolve_transcribe_runtime
            original_mlx = transcribe_module._transcribe_with_mlx_backend
            try:
                transcribe_module._ensure_bili_analyzer_import = lambda: None
                transcribe_module.resolve_transcribe_runtime = lambda **_kwargs: {
                    "profile": "apple_silicon",
                    "device": "mps",
                    "compute_type": "int8_float16",
                    "reason": "apple silicon",
                }

                def fail_mlx(**_kwargs):
                    raise RuntimeError("mlx-whisper is not installed")

                transcribe_module._transcribe_with_mlx_backend = fail_mlx
                payload, result = transcribe_module.transcribe_with_backend(
                    input_path=video_path,
                    output_dir=out_dir,
                    platform_profile="apple_silicon",
                )
            finally:
                transcribe_module._ensure_bili_analyzer_import = original_ensure
                transcribe_module.resolve_transcribe_runtime = original_runtime
                transcribe_module._transcribe_with_mlx_backend = original_mlx
                if old_pkg is None:
                    sys.modules.pop("bili_analyzer", None)
                else:
                    sys.modules["bili_analyzer"] = old_pkg
                if old_core is None:
                    sys.modules.pop("bili_analyzer.core", None)
                else:
                    sys.modules["bili_analyzer.core"] = old_core

            self.assertEqual(payload.text, "cpu hello")
            self.assertEqual(calls["device"], "cpu")
            self.assertEqual(calls["compute_type"], "int8")
            self.assertEqual(result["runtime_profile"]["profile"], "apple_silicon_cpu_fallback")


if __name__ == "__main__":
    unittest.main()
