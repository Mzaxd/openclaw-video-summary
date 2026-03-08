from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class AsrRuntimeProfile:
    profile_name: str
    device: str
    compute_type: str
    reason: str


def resolve_asr_runtime_profile(
    *,
    platform_name: str,
    machine: str,
    requested_profile: str,
    requested_device: str,
    requested_compute_type: str,
    env: Mapping[str, str],
) -> AsrRuntimeProfile:
    if requested_device != "auto" or requested_compute_type != "int8":
        return AsrRuntimeProfile(
            profile_name="manual_override",
            device=requested_device,
            compute_type=requested_compute_type,
            reason="explicit device/compute",
        )

    profile = (requested_profile or "auto").strip().lower()
    os_name = (platform_name or "").strip().lower()
    arch = (machine or "").strip().lower()
    has_nvidia = str(env.get("OCVS_HAS_NVIDIA", "")).strip().lower() in {"1", "true", "yes"}

    if profile == "nvidia" or (profile == "auto" and os_name == "linux" and has_nvidia):
        return AsrRuntimeProfile(
            profile_name="nvidia_cuda",
            device="cuda",
            compute_type="float16",
            reason="nvidia gpu detected",
        )
    if profile == "apple_silicon" or (profile == "auto" and os_name == "darwin" and arch in {"arm64", "aarch64"}):
        return AsrRuntimeProfile(
            profile_name="apple_silicon",
            device="mps",
            compute_type="int8_float16",
            reason="apple silicon",
        )
    if profile == "intel":
        return AsrRuntimeProfile(
            profile_name="intel_cpu",
            device="cpu",
            compute_type="int8",
            reason="intel/openvino-compatible fallback",
        )
    if profile == "amd":
        return AsrRuntimeProfile(
            profile_name="amd_gpu",
            device="cuda",
            compute_type="float16",
            reason="amd/rocm-compatible path",
        )
    return AsrRuntimeProfile(
        profile_name="cpu_fallback",
        device="cpu",
        compute_type="int8",
        reason="safe default",
    )
