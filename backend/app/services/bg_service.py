"""
Background removal using rembg + U2Net model.
100% FREE — downloads model automatically on first run (~170MB).
Works on CPU — no GPU needed.
"""
from rembg import remove, new_session
from PIL import Image
import io, asyncio, logging
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=2)
_session = None


def _load_session():
    global _session
    if _session is None:
        logger.info("Loading U2Net model (first time: ~170MB download)...")
        _session = new_session("u2net")
        logger.info("✅ U2Net model ready")
    return _session


def _do_remove(image_bytes: bytes, bg_color: str = None) -> bytes:
    session = _load_session()
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    result = remove(img, session=session)

    if bg_color:
        bg = Image.new("RGBA", result.size, bg_color)
        bg.paste(result, mask=result.split()[3])
        out = bg.convert("RGB")
        buf = io.BytesIO()
        out.save(buf, format="JPEG", quality=95)
    else:
        buf = io.BytesIO()
        result.save(buf, format="PNG")  # Keep transparency

    return buf.getvalue()


async def remove_background(image_bytes: bytes, bg_color: str = None) -> bytes:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _do_remove, image_bytes, bg_color)
