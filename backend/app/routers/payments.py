from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import razorpay, hmac, hashlib, logging
from app.utils.auth_middleware import auth, User
from app.services.firebase_service import activate_pro
from app.config import get_settings

router = APIRouter()
logger = logging.getLogger(__name__)
settings = get_settings()

PLANS = {
    "pro_monthly": {"amount": 19900, "currency": "INR", "days": 30},
    "pro_annual":  {"amount": 99900, "currency": "INR", "days": 365},
}

class OrderReq(BaseModel):
    plan: str

class VerifyReq(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    plan: str

@router.post("/create-order")
async def create_order(body: OrderReq, user: User = Depends(auth)):
    if body.plan not in PLANS:
        raise HTTPException(400, "Invalid plan.")
    p = PLANS[body.plan]
    client = razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))
    try:
        order = client.order.create({
            "amount": p["amount"], "currency": p["currency"],
            "receipt": f"{user.uid[:8]}_{body.plan}",
        })
        return {
            "order_id": order["id"],
            "amount": p["amount"],
            "currency": p["currency"],
            "key_id": settings.razorpay_key_id,
        }
    except Exception as e:
        logger.error(f"Razorpay error: {e}")
        raise HTTPException(500, "Payment failed to initiate.")

@router.post("/verify")
async def verify(body: VerifyReq, user: User = Depends(auth)):
    msg = f"{body.razorpay_order_id}|{body.razorpay_payment_id}"
    expected = hmac.new(settings.razorpay_key_secret.encode(), msg.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, body.razorpay_signature):
        raise HTTPException(400, "Payment verification failed.")
    if body.plan not in PLANS:
        raise HTTPException(400, "Invalid plan.")
    expiry = await activate_pro(user.uid, body.plan, PLANS[body.plan]["days"], body.razorpay_payment_id)
    return {"success": True, "plan": "pro", "expires": expiry.isoformat()}
