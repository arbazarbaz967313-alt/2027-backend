"""
Watermark removal using OpenCV inpainting (TELEA algorithm).
100% FREE — no external API, runs on CPU.
"""
import cv2
import numpy as np
from PIL import Image
import io, asyncio, logging
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=2)


def _detect_watermark_mask(img_np: np.ndarray) -> np.ndarray:
    """
    Auto-detect watermark by finding semi-transparent or light-colored
    text-like regions. Works for most common watermarks.
    """
    h, w = img_np.shape[:2]
    gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
    mask = np.zeros((h, w), dtype=np.uint8)

    # Check all 4 corners (most watermarks are in corners)
    regions = [
        (0, 0, w // 3, h // 8),                          # Top-left
        (w * 2 // 3, 0, w, h // 8),                      # Top-right
        (0, h * 7 // 8, w // 3, h),                      # Bottom-left
        (w * 2 // 3, h * 7 // 8, w, h),                  # Bottom-right
        (w // 4, h * 7 // 8, w * 3 // 4, h),             # Bottom-center
    ]

    for x1, y1, x2, y2 in regions:
        region = gray[y1:y2, x1:x2]
        # Detect bright (white/light) text-like areas
        _, thresh = cv2.threshold(region, 200, 255, cv2.THRESH_BINARY)
        coverage = np.sum(thresh > 0) / thresh.size
        if 0.02 < coverage < 0.5:  # Has some bright pixels but not all
            # Dilate to cover full watermark text
            kernel = np.ones((5, 5), np.uint8)
            dilated = cv2.dilate(thresh, kernel, iterations=3)
            mask[y1:y2, x1:x2] = dilated

    return mask


def _do_remove_watermark(image_bytes: bytes, mask_bytes: bytes = None) -> bytes:
    # Decode image
    np_arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if mask_bytes:
        # Use user-provided mask
        mask_arr = np.frombuffer(mask_bytes, np.uint8)
        mask = cv2.imdecode(mask_arr, cv2.IMREAD_GRAYSCALE)
        _, mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
    else:
        # Auto-detect
        mask = _detect_watermark_mask(img)

    if mask is None or np.sum(mask) == 0:
        # No watermark found — return original
        _, buf = cv2.imencode(".png", img)
        return buf.tobytes()

    # Inpaint using TELEA algorithm (high quality, free)
    result = cv2.inpaint(img, mask, inpaintRadius=5, flags=cv2.INPAINT_TELEA)

    _, buf = cv2.imencode(".png", result)
    return buf.tobytes()


async def remove_watermark(image_bytes: bytes, mask_bytes: bytes = None) -> bytes:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _do_remove_watermark, image_bytes, mask_bytes)
