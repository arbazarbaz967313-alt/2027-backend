import firebase_admin
from firebase_admin import credentials, firestore, storage, auth as fb_auth
from app.config import get_settings
from datetime import datetime, date, timedelta
import logging

logger = logging.getLogger(__name__)
settings = get_settings()
_db = None
_bucket = None


def init_firebase():
    global _db, _bucket
    if not firebase_admin._apps:
        cred = credentials.Certificate(settings.firebase_creds)
        firebase_admin.initialize_app(cred, {
            "storageBucket": settings.firebase_storage_bucket
        })
    _db = firestore.client()
    _bucket = storage.bucket()
    logger.info("✅ Firebase ready")


def get_db():
    return _db


async def verify_token(token: str) -> dict:
    return fb_auth.verify_id_token(token)


async def get_user_plan(uid: str) -> str:
    doc = _db.collection("users").document(uid).get()
    if not doc.exists:
        _db.collection("users").document(uid).set({
            "plan": "free",
            "daily_usage": 0,
            "usage_date": date.today().isoformat(),
            "created_at": firestore.SERVER_TIMESTAMP,
        })
        return "free"
    data = doc.to_dict()
    plan = data.get("plan", "free")
    if plan == "pro":
        expiry = data.get("plan_expiry")
        if expiry:
            exp_dt = expiry if isinstance(expiry, datetime) else datetime.fromisoformat(str(expiry))
            exp_dt = exp_dt.replace(tzinfo=None)
            if exp_dt < datetime.utcnow():
                _db.collection("users").document(uid).update({"plan": "free"})
                return "free"
    return plan


async def check_and_use(uid: str, is_pro: bool) -> bool:
    if is_pro:
        return True
    today = date.today().isoformat()
    ref = _db.collection("users").document(uid)

    @firestore.transactional
    def run(transaction, ref):
        doc = ref.get(transaction=transaction)
        data = doc.to_dict() or {}
        count = data.get("daily_usage", 0) if data.get("usage_date") == today else 0
        if count >= settings.free_daily_limit:
            return False
        transaction.update(ref, {"daily_usage": count + 1, "usage_date": today})
        return True

    return run(_db.transaction(), ref)


async def save_history(uid: str, job_id: str, url: str, tool: str):
    _db.collection("users").document(uid).collection("history").document(job_id).set({
        "job_id": job_id, "tool": tool,
        "result_url": url,
        "created_at": firestore.SERVER_TIMESTAMP,
        "status": "done",
    })


async def upload_file(data: bytes, path: str, mime: str) -> str:
    blob = _bucket.blob(path)
    blob.upload_from_string(data, content_type=mime)
    url = blob.generate_signed_url(expiration=timedelta(days=7), method="GET")
    return url


async def get_profile(uid: str) -> dict:
    doc = _db.collection("users").document(uid).get()
    return doc.to_dict() if doc.exists else {}


async def activate_pro(uid: str, plan: str, days: int, payment_id: str):
    expiry = datetime.utcnow() + timedelta(days=days)
    _db.collection("users").document(uid).update({
        "plan": "pro", "plan_expiry": expiry,
        "plan_key": plan, "payment_id": payment_id,
        "upgraded_at": firestore.SERVER_TIMESTAMP,
    })
    return expiry
