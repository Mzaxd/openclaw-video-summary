import unittest

from openclaw_video_summary.asr.transcribe import TranscriptPayload


class TranscribeContractTest(unittest.TestCase):
    def test_transcript_payload_has_text_and_segments(self) -> None:
        payload = TranscriptPayload(
            text="hello",
            segments=[{"start": 0.0, "end": 1.0, "text": "hello"}],
        )

        self.assertEqual(payload.text, "hello")
        self.assertEqual(payload.segments[0]["text"], "hello")


if __name__ == "__main__":
    unittest.main()
