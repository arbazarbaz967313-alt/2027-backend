from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
import uuid, logging, asyncio, json
from app.utils.auth_middleware import auth, User
from app.services.video_service import process_video
from app.services.firebase_service import check_and_use, save_history, upload_file, get_db

router = APIRouter()
logger = logging.getLogger(__name__)
TOOLS = ["compress", "convert", "trim", "remove_audio", "extract_audio"]

@router.post("/process")
async def video(
    file: UploadFile = File(...),
    tool: str = Form(...),
    params: str = Form("{}"),
    user: User = Depends(auth),
):
    if tool not in TOOLS:
        raise HTTPException(400, f"Tool must be one of: {TOOLS}")
    if not await check_and_use(user.uid, user.is_pro):
        raise HTTPException(429, "Daily limit reached. Upgrade to Pro.")
    max_mb = 100 if user.is_pro else 50
    video_bytes = await file.read()
    if len(video_bytes) > max_mb * 1024 * 1024:
        raise HTTPException(413, f"Max {max_mb}MB.")
    job_id = str(uuid.uuid4())
    db = get_db()
    db.collection("jobs").document(job_id).set({"status": "queued", "uid": user.uid})
    asyncio.create_task(_run(video_bytes, tool, params, job_id, user.uid))
    return {"job_id": job_id, "status": "queued"}

async def _run(video_bytes, tool, params_str, job_id, uid):
    db = get_db()
    try:
        db.collection("jobs").document(job_id).update({"status": "processing"})
        result, ext = await process_video(video_bytes, tool, json.loads(params_str))
        mime = "audio/mpeg" if ext == "mp3" else "video/mp4"
        url = await upload_file(result, f"video/{uid}/{job_id}.{ext}", mime)
        await save_history(uid, job_id, url, f"video_{tool}")
        db.collection("jobs").document(job_id).update({"status": "done", "result_url": url})
    except Exception as e:
        logger.error(f"Video job failed {job_id}: {e}")
        db.collection("jobs").document(job_id).update({"status": "failed"})
