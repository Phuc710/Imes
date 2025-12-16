import logging
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.logging import setup_logging
from app.api.v1.routes_ocr import router as ocr_router
from app.models.loader import load_model_once

setup_logging()
logger = logging.getLogger("main")

app = FastAPI(title=settings.APP_NAME)

@app.on_event("startup")
def on_startup():
    # load model 1 lần khi start
    load_model_once()
    logger.info("Startup complete.")

@app.get("/")
def root():
    return JSONResponse({"message": "OCR API", "version": "1.0", "endpoints": {"/health": "GET", "/v1/ocr": "POST"}})

@app.get("/health")
def health():
    return {"status": "CÒN SỐNG"}

app.include_router(ocr_router)
