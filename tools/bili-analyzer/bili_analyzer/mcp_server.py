from __future__ import annotations

from pathlib import Path

from .core import analyze_frames_dir, prepare_video as core_prepare_video
from .summarizer import summarize_video as core_summarize_video


def run() -> None:
    try:
        from mcp.server.fastmcp import FastMCP
    except Exception as exc:  # pragma: no cover
        raise SystemExit(
            "Missing dependency `mcp`. Install with: pip install -e tools/bili-analyzer"
        ) from exc

    app = FastMCP("bili-analyzer")

    @app.tool()
    def prepare_video(
        url: str,
        output: str = "./tmp",
        fps: float = 1.0,
        similarity: float = 0.80,
        no_dedup: bool = False,
        video_only: bool = False,
        frames_only: bool = False,
    ) -> dict:
        """Prepare a Bilibili video: download, extract frames, and dedup adjacent frames."""
        return core_prepare_video(
            url=url,
            output=output,
            fps=fps,
            similarity=similarity,
            no_dedup=no_dedup,
            video_only=video_only,
            frames_only=frames_only,
        )

    @app.tool()
    def analyze_frames(images_dir: str) -> dict:
        """Analyze an image directory and emit basic frame index and statistics."""
        return analyze_frames_dir(Path(images_dir).expanduser().resolve())

    @app.tool()
    def summarize_video(
        url: str,
        output: str = "./tmp",
        mode: str = "fast",
        language: str = "auto",
        asr_model: str = "small",
        llm_model: str = "glm-4.6v",
        api_base: str | None = None,
        api_key: str | None = None,
    ) -> dict:
        """Generate Chinese summary and timeline for a video URL."""
        return core_summarize_video(
            url=url,
            output=output,
            mode=mode,
            language=language,
            asr_model=asr_model,
            llm_model=llm_model,
            api_base=api_base,
            api_key=api_key,
        )

    app.run()


if __name__ == "__main__":
    run()
