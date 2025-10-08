from pydantic_settings import BaseSettings, SettingsConfigDict

env_file = ".env"


class Settings(BaseSettings):
    # Stream
    RTSP_USERNAME: str = ""
    RTSP_PASSWORD: str = ""
    RTSP_HOST_IP_ADDRESS: str = ""
    RTSP_STREAM_NAME: str = ""

    # Database
    POSTGRES_USER: str = "schrodinger"
    POSTGRES_PWD: str = "schrodinger"
    POSTGRES_HOST: str = "127.0.0.1"
    POSTGRES_PORT: int = 5432
    POSTGRES_DATABASE: str = "schrodinger_development"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_SYNC_POOL_SIZE: int = 1  # Specific pool size for sync connection: since we only use it in OAuth2 router, don't waste resources.
    DATABASE_POOL_RECYCLE_SECONDS: int = 600  # 10 minutes
    DATABASE_COMMAND_TIMEOUT_SECONDS: float = 30.0
    DATABASE_STREAM_YIELD_PER: int = 100

    POSTGRES_READ_USER: str | None = None
    POSTGRES_READ_PWD: str | None = None
    POSTGRES_READ_HOST: str | None = None
    POSTGRES_READ_PORT: int | None = None
    POSTGRES_READ_DATABASE: str | None = None

    # Redis
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # Celery
    CELERY_BROKER_URL: str = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
    CELERY_BACKEND_URL: str = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

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
