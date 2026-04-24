## ── bgremove.py ──────────────────────────────────────────
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
import uuid, logging
from app.utils.auth_middleware import auth, User
from app.services.bg_service import remove_background
from app.services.firebase_service import check_and_use, save_history, upload_file

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/photo")
async def bg_photo(
    file: UploadFile = File(...),
    bg_color: str = Form(None),
    user: User = Depends(auth),
):
    if not await check_and_use(user.uid, user.is_pro):
        raise HTTPException(429, "Daily limit reached. Upgrade to Pro.")
    img = await file.read()
    if len(img) > 20 * 1024 * 1024:
        raise HTTPException(413, "Max 20MB.")
    try:
        result = await remove_background(img, bg_color)
    except Exception as e:
        logger.error(f"BG remove error [{user.uid}]: {e}")
        raise HTTPException(500, "Processing failed.")
    job_id = str(uuid.uuid4())
    mime = "image/jpeg" if bg_color else "image/png"
    ext = "jpg" if bg_color else "png"
    url = await upload_file(result, f"bgremove/{user.uid}/{job_id}.{ext}", mime)
    await save_history(user.uid, job_id, url, "bgremove")
    return {"job_id": job_id, "result_url": url, "status": "done"}
