from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
import uuid, logging
from app.utils.auth_middleware import auth, User
from app.services.watermark_service import remove_watermark
from app.services.firebase_service import check_and_use, save_history, upload_file

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/remove")
async def watermark_remove(
    file: UploadFile = File(...),
    mask: UploadFile = File(None),
    user: User = Depends(auth),
):
    if not await check_and_use(user.uid, user.is_pro):
        raise HTTPException(429, "Daily limit (5/day) reached. Upgrade to Pro for unlimited.")

    img = await file.read()
    if len(img) > 20 * 1024 * 1024:
        raise HTTPException(413, "Image too large. Max 20MB.")

    mask_bytes = await mask.read() if mask else None

    try:
        result = await remove_watermark(img, mask_bytes)
    except Exception as e:
        logger.error(f"Watermark error [{user.uid}]: {e}")
        raise HTTPException(500, "Processing failed. Please try again.")

    job_id = str(uuid.uuid4())
    url = await upload_file(result, f"watermark/{user.uid}/{job_id}.png", "image/png")
    await save_history(user.uid, job_id, url, "watermark")
    return {"job_id": job_id, "result_url": url, "status": "done"}
