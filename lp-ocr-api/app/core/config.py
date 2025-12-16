from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    APP_NAME: str = "lp-ocr-api"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # model
    MODEL_PATH: str = "app/models/weights/LP_ocr.pt"
    DEVICE: str = "auto"  # "auto" | "cpu" | "cuda"

    # inference defaults
    YOLO_CONF: float = 0.10
    YOLO_IOU: float = 0.45
    OCR_CONF_THRESHOLD: float = 0.50

    # upload constraints
    MAX_UPLOAD_MB: int = 5


settings = Settings()
