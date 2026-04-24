from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_env: str = "development"
    secret_key: str = "dev-only-change-in-prod"

    firebase_project_id: str = ""
    firebase_private_key_id: str = ""
    firebase_private_key: str = ""
    firebase_client_email: str = ""
    firebase_client_id: str = ""
    firebase_storage_bucket: str = ""

    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""

    free_daily_limit: int = 5
    max_image_mb: int = 20
    max_video_mb: int = 100

    @property
    def firebase_creds(self) -> dict:
        return {
            "type": "service_account",
            "project_id": self.firebase_project_id,
            "private_key_id": self.firebase_private_key_id,
            "private_key": self.firebase_private_key.replace("\\n", "\n"),
            "client_email": self.firebase_client_email,
            "client_id": self.firebase_client_id,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()
