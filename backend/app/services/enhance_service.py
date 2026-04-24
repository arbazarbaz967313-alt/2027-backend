"""
Image enhancement using PIL + OpenCV basic ops.
100% FREE - no dnn_superres needed, works on Render free tier.
"""
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import io
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=1)


def _do_enhance(image_bytes: bytes, scale: int, enhance_type: str) -> bytes:
    # Decode
    np_arr = np.frombuffer(image_bytes, np.uint8)
    img_cv = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if enhance_type == "upscale":
        h, w = img_cv.shape[:2]
        # Lanczos upscale — good quality, no special module needed
        result = cv2.resize(
            img_cv,
            (w * scale, h * scale),
            interpolation=cv2.INTER_LANCZOS4
        )

    elif enhance_type == "denoise":
        result = cv2.fastNlMeansDenoisingColored(img_cv, None, 10, 10, 7, 21)

    elif enhance_type == "sharpen":
        kernel = np.array([[0, -1, 0],
                           [-1, 5, -1],
                           [0, -1, 0]])
        result = cv2.filter2D(img_cv, -1, kernel)

    elif enhance_type == "brightness":
        # CLAHE auto brightness/contrast
        lab = cv2.cvtColor(img_cv, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        result = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)

    else:
        result = img_cv

    _, buf = cv2.imencode(".png", result)
    return buf.tobytes()


async def enhance_image(image_bytes: bytes, scale: int = 2, enhance_type: str = "upscale") -> bytes:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _do_enhance, image_bytes, scale, enhance_type)
