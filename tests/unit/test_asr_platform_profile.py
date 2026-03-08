import unittest

from openclaw_video_summary.asr.platform_profile import resolve_asr_runtime_profile


class AsrPlatformProfileTest(unittest.TestCase):
    def test_linux_x86_with_nvidia_prefers_cuda_fp16(self) -> None:
        profile = resolve_asr_runtime_profile(
            platform_name="linux",
            machine="x86_64",
            requested_profile="auto",
            requested_device="auto",
            requested_compute_type="int8",
            env={"OCVS_HAS_NVIDIA": "1"},
        )
        self.assertEqual(profile.profile_name, "nvidia_cuda")
        self.assertEqual(profile.device, "cuda")
        self.assertEqual(profile.compute_type, "float16")

    def test_macos_arm_prefers_mps_int8_float16(self) -> None:
        profile = resolve_asr_runtime_profile(
            platform_name="darwin",
            machine="arm64",
            requested_profile="auto",
            requested_device="auto",
            requested_compute_type="int8",
            env={},
        )
        self.assertEqual(profile.profile_name, "apple_silicon")
        self.assertEqual(profile.device, "mps")
        self.assertEqual(profile.compute_type, "int8_float16")

    def test_explicit_device_compute_override_profile(self) -> None:
        profile = resolve_asr_runtime_profile(
            platform_name="darwin",
            machine="arm64",
            requested_profile="auto",
            requested_device="cpu",
            requested_compute_type="int8",
            env={},
        )
        self.assertEqual(profile.profile_name, "manual_override")
        self.assertEqual(profile.device, "cpu")
        self.assertEqual(profile.compute_type, "int8")


if __name__ == "__main__":
    unittest.main()
