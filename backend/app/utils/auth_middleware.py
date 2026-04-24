from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import auth as fb_auth
from app.services.firebase_service import get_user_plan
import logging

logger = logging.getLogger(__name__)
bearer = HTTPBearer()


class User:
    def __init__(self, uid: str, email: str, plan: str):
        self.uid = uid
        self.email = email
        self.plan = plan

    @property
    def is_pro(self):
        return self.plan == "pro"


async def auth(creds: HTTPAuthorizationCredentials = Depends(bearer)) -> User:
    try:
        decoded = fb_auth.verify_id_token(creds.credentials)
    except fb_auth.ExpiredIdTokenError:
        raise HTTPException(401, "Session expired. Please login again.")
    except Exception:
        raise HTTPException(401, "Invalid token.")
    uid = decoded["uid"]
    plan = await get_user_plan(uid)
    return User(uid=uid, email=decoded.get("email", ""), plan=plan)
