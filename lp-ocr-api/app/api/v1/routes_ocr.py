import logging
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Query, HTTPException
import os
from pathlib import Path

from app.services.image_io import decode_image_bytes
from app.services.ocr_service import run_ocr
from app.models.loader import get_model
from app.api.v1.schemas import OCRResponse

router = APIRouter(prefix="/v1", tags=["ocr"])
logger = logging.getLogger("routes_ocr")

# Tạo folder lưu ảnh
IMG_FOLDER = Path(__file__).parent.parent.parent.parent / "img"
IMG_FOLDER.mkdir(exist_ok=True)


@router.post("/ocr", response_model=OCRResponse)
async def ocr_endpoint(
    file: UploadFile = File(...),
    conf_threshold: float | None = Query(default=None, ge=0.0, le=1.0),
    camera_id: int | None = Query(default=None),
):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    content = await file.read()
    if not content:
        logger.warning(f"[{timestamp}] Empty file uploaded")
        raise HTTPException(status_code=400, detail="Empty file")

    img = decode_image_bytes(content)
    if img is None:
        logger.warning(f"[{timestamp}] Cannot decode image: {file.filename}")
        raise HTTPException(status_code=400, detail="Cannot decode image")
    
    model = get_model()
    result = run_ocr(model, img, conf_threshold=conf_threshold)
    
    text = result.get('text', '')
    status = "200"
    logger.info(f"[{timestamp}] text='{text}' | status={status}")
    
    # Lưu ảnh vào folder img
    try:
        filename = f"ocr_{camera_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        img_path = IMG_FOLDER / filename
        
        with open(img_path, 'wb') as f:
            f.write(content)
        logger.info(f"[{timestamp}] Image saved: {img_path}")
    except Exception as e:
        logger.error(f"[{timestamp}] Failed to save image: {str(e)}")
    
    # Return text và timestamp
    return OCRResponse(text=text, timestamp=timestamp)
