from fastapi import APIRouter, Depends, HTTPException
from app.utils.auth_middleware import auth, User
from app.services.firebase_service import get_db

router = APIRouter()

@router.get("/{job_id}")
async def status(job_id: str, user: User = Depends(auth)):
    db = get_db()
    doc = db.collection("jobs").document(job_id).get()
    if not doc.exists:
        raise HTTPException(404, "Job not found.")
    data = doc.to_dict()
    if data.get("uid") != user.uid:
        raise HTTPException(403, "Access denied.")
    return {"job_id": job_id, "status": data.get("status"), "result_url": data.get("result_url")}

@router.get("/history/list")
async def history(user: User = Depends(auth)):
    db = get_db()
    docs = (db.collection("users").document(user.uid)
            .collection("history")
            .order_by("created_at", direction="DESCENDING")
            .limit(30).stream())
    return {"history": [d.to_dict() for d in docs]}
