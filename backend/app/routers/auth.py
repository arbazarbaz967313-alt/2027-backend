## ── auth.py ──────────────────────────────────────────────
from fastapi import APIRouter, Depends, HTTPException
from firebase_admin import auth as fb_auth
from app.utils.auth_middleware import auth, User
from app.services.firebase_service import get_profile, get_db

router = APIRouter()

@router.get("/me")
async def me(user: User = Depends(auth)):
    profile = await get_profile(user.uid)
    return {
        "uid": user.uid,
        "email": user.email,
        "plan": user.plan,
        "is_pro": user.is_pro,
        "daily_usage": profile.get("daily_usage", 0),
        "plan_expiry": str(profile.get("plan_expiry", "")),
    }

@router.delete("/account")
async def delete(user: User = Depends(auth)):
    get_db().collection("users").document(user.uid).delete()
    fb_auth.delete_user(user.uid)
    return {"success": True}
