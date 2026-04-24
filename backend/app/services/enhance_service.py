"""
Image enhancement using OpenCV DNN Super Resolution.
Models: EDSR, ESPCN, FSRCNN — all FREE and open source.
Downloads ~5MB model on first use.
"""
import cv2
import numpy as np
from cv2 import dnn_superres
from PIL import Image, ImageEnhance, ImageFilter
import io, asyncio, logging, os, urllib.request
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=1)
_sr = None

# Free OpenCV super resolution model
MODEL_URL = "https://github.com/Saafke/EDSR_Tensorflow/raw/master/models/EDSR_x2.pb"
MODEL_PATH = "/tmp/EDSR_x2.pb"


def _load_sr_model():
    global _sr
    if _sr is not None:
        return _sr
    if not os.path.exists(MODEL_PATH):
        logger.info("Downloading EDSR model (~5MB)...")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        logger.info("✅ EDSR model downloaded")
    sr = dnn_superres.DnnSuperResImpl_create()
    sr.readModel(MODEL_PATH)
    sr.setModel("edsr", 2)
    _sr = sr
    return _sr


def _do_enhance(image_bytes: bytes, scale: int, enhance_type: str) -> bytes:
    np_arr = np.frombuffer(image_bytes, np.uint8)
    img_cv = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if enhance_type == "upscale":
        try:
            sr = _load_sr_model()
            result = sr.upsample(img_cv)
            if scale == 4:
                # Apply 2x again for 4x total
                result = sr.upsample(result)
        except Exception as e:
            logger.warning(f"SR model failed, using bicubic: {e}")
            h, w = img_cv.shape[:2]
            result = cv2.resize(img_cv, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)

    elif enhance_type == "denoise":
        result = cv2.fastNlMeansDenoisingColored(img_cv, None, 10, 10, 7, 21)

    elif enhance_type == "sharpen":
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        result = cv2.filter2D(img_cv, -1, kernel)

    elif enhance_type == "brightness":
        # Auto brightness + contrast
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
