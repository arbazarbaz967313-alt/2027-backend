from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
import uuid, logging
from app.utils.auth_middleware import auth, User
from app.services.enhance_service import enhance_image
from app.services.firebase_service import check_and_use, save_history, upload_file

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/image")
async def enhance(
    file: UploadFile = File(...),
    scale: int = Form(2),
    enhance_type: str = Form("upscale"),
    user: User = Depends(auth),
):
    if scale == 4 and not user.is_pro:
        raise HTTPException(403, "4x upscale requires Pro.")
    if not await check_and_use(user.uid, user.is_pro):
        raise HTTPException(429, "Daily limit reached. Upgrade to Pro.")
    img = await file.read()
    if len(img) > 20 * 1024 * 1024:
        raise HTTPException(413, "Max 20MB.")
    try:
        result = await enhance_image(img, scale, enhance_type)
    except Exception as e:
        logger.error(f"Enhance error [{user.uid}]: {e}")
        raise HTTPException(500, "Enhancement failed.")
    job_id = str(uuid.uuid4())
    url = await upload_file(result, f"enhance/{user.uid}/{job_id}.png", "image/png")
    await save_history(user.uid, job_id, url, "enhance")
    return {"job_id": job_id, "result_url": url, "status": "done", "scale": scale}
