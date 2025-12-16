import logging
from pathlib import Path
import torch

from app.core.config import settings

logger = logging.getLogger("model_loader")

_model = None


def _resolve_device() -> str:
    if settings.DEVICE == "cpu":
        return "cpu"
    if settings.DEVICE == "cuda":
        return "cuda"
    # auto
    return "cuda" if torch.cuda.is_available() else "cpu"


def load_model_once():
    global _model
    if _model is not None:
        return _model

    model_path = Path(settings.MODEL_PATH)
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")

    device = _resolve_device()
    logger.info("Loading model: %s | device=%s", model_path, device)

    model = torch.hub.load(
        "ultralytics/yolov5",
        "custom",
        path=str(model_path),
        force_reload=False,
    )
    model.to(device)

    # yolo params
    model.conf = float(settings.YOLO_CONF)
    model.iou = float(settings.YOLO_IOU)

    _model = model
    logger.info("Model loaded OK.")
    return _model


def get_model():
    if _model is None:
        return load_model_once()
    return _model
