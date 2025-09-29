from pydantic_settings import BaseSettings, SettingsConfigDict

env_file = ".env"


class Settings(BaseSettings):
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_BACKEND_URL: str = "redis://localhost:6379/0"

    RTSP_USERNAME: str = ""
    RTSP_PASSWORD: str = ""
    RTSP_HOST_IP_ADDRESS: str = ""
    RTSP_STREAM_NAME: str = ""

    # Downloadable files
    S3_FILES_BUCKET_NAME: str = "schrodinger-s3"
    S3_FILES_PUBLIC_BUCKET_NAME: str = "schrodinger-s3-public"
    S3_FILES_PRESIGN_TTL: int = 600  # 10 minutes
    S3_FILES_DOWNLOAD_SECRET: str = "supersecret"
    S3_FILES_DOWNLOAD_SALT: str = "saltysalty"
    # Override to http://127.0.0.1:9000 in .env during development
    S3_ENDPOINT_URL: str | None = None

    MINIO_USER: str = "schrodinger"
    MINIO_PWD: str = "schrodinger123"

    model_config = SettingsConfigDict(env_prefix="schrodinger_",
                                      env_file_encoding="utf-8",
                                      case_sensitive=False,
                                      env_file=env_file,
                                      extra="allow")


settings = Settings()
