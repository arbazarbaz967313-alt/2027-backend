"""
Video processing using FFmpeg — 100% FREE.
ffmpeg binary installed via apt-get in render.yaml build command.
"""
import ffmpeg
import asyncio, tempfile, os, logging
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=1)


def _compress(inp: str, out: str, quality: str):
    crf = {"low": 28, "medium": 23, "high": 18}.get(quality, 23)
    ffmpeg.input(inp).output(
        out, vcodec="libx264", crf=crf,
        acodec="aac", movflags="+faststart", preset="fast"
    ).overwrite_output().run(quiet=True)


def _convert(inp: str, out: str):
    ffmpeg.input(inp).output(out).overwrite_output().run(quiet=True)


def _trim(inp: str, out: str, start: float, end: float):
    ffmpeg.input(inp, ss=start, t=end - start).output(
        out, c="copy"
    ).overwrite_output().run(quiet=True)


def _remove_audio(inp: str, out: str):
    ffmpeg.input(inp).output(out, an=None, vcodec="copy").overwrite_output().run(quiet=True)


def _extract_audio(inp: str, out: str):
    ffmpeg.input(inp).output(out, vn=None, acodec="libmp3lame").overwrite_output().run(quiet=True)


def _run_tool(video_bytes: bytes, tool: str, params: dict) -> tuple[bytes, str]:
    fmt_map = {"compress": "mp4", "convert": params.get("format", "mp4"),
               "trim": "mp4", "remove_audio": "mp4", "extract_audio": "mp3"}
    ext = fmt_map.get(tool, "mp4")

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        f.write(video_bytes)
        inp = f.name

    out = inp.replace(".mp4", f"_out.{ext}")
    try:
        if tool == "compress":
            _compress(inp, out, params.get("quality", "medium"))
        elif tool == "convert":
            _convert(inp, out)
        elif tool == "trim":
            _trim(inp, out, float(params.get("start", 0)), float(params.get("end", 10)))
        elif tool == "remove_audio":
            _remove_audio(inp, out)
        elif tool == "extract_audio":
            _extract_audio(inp, out)
        with open(out, "rb") as f:
            return f.read(), ext
    finally:
        if os.path.exists(inp): os.unlink(inp)
        if os.path.exists(out): os.unlink(out)


async def process_video(video_bytes: bytes, tool: str, params: dict) -> tuple[bytes, str]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _run_tool, video_bytes, tool, params)
