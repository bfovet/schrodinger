from pydantic_settings import BaseSettings, SettingsConfigDict

env_file = ".env"


class Settings(BaseSettings):
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_BACKEND_URL: str = "redis://localhost:6379/0"

    SCHRODINGER_RTSP_USERNAME: str
    SCHRODINGER_RTSP_PASSWORD: str
    SCHRODINGER_RTSP_HOST_IP_ADDRESS: str
    SCHRODINGER_RTSP_STREAM_NAME: str

    model_config = SettingsConfigDict(env_file=env_file)


settings = Settings()
