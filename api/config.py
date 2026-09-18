"""
VĀSTU API Configuration
Pydantic Settings for environment variables.
"""

import os
from pydantic import BaseModel

class Settings(BaseModel):
    app_name: str = "VĀSTU Spatial Computing Platform API"
    app_version: str = "1.0.0"
    port: int = int(os.getenv("PORT", "8000"))
    jwt_secret: str = os.getenv("JWT_SECRET", "vastu_production_secure_jwt_signing_key_994829384729103847291028347")
    database_url: str = os.getenv("DATABASE_URL", "postgresql://vastu_user:vastu_secure_password_2026@localhost:5432/vastu_db")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    s3_endpoint_url: str = os.getenv("S3_ENDPOINT_URL", "http://localhost:9000")
    s3_bucket: str = os.getenv("S3_BUCKET", "vastu-artifacts")
    upload_dir: str = os.getenv("UPLOAD_DIR", "uploads")

settings = Settings()
