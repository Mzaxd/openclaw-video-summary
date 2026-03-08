import unittest

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


if __name__ == "__main__":
    unittest.main()
