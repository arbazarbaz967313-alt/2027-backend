from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn, logging, os

from app.config import get_settings
from app.services.firebase_service import init_firebase
from app.routers import auth, watermark, bgremove, enhance, video, jobs, payments

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 ClearCut API starting...")
    init_firebase()
    yield
    logger.info("👋 Shutdown")

app = FastAPI(
    title="ClearCut API",
    version="1.0.0",
    docs_url="/docs" if settings.app_env != "production" else None,
    redoc_url=None,
    openapi_url="/openapi.json" if settings.app_env != "production" else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_err(request: Request, exc: Exception):
    logger.error(f"Error: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Server error."})

app.include_router(auth.router,      prefix="/api/v1/auth",      tags=["Auth"])
app.include_router(watermark.router, prefix="/api/v1/watermark", tags=["Watermark"])
app.include_router(bgremove.router,  prefix="/api/v1/bgremove",  tags=["BG Remove"])
app.include_router(enhance.router,   prefix="/api/v1/enhance",   tags=["Enhance"])
app.include_router(video.router,     prefix="/api/v1/video",     tags=["Video"])
app.include_router(jobs.router,      prefix="/api/v1/jobs",      tags=["Jobs"])
app.include_router(payments.router,  prefix="/api/v1/payments",  tags=["Payments"])

@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
