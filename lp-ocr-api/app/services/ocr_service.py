from __future__ import annotations

import logging
import time
import pandas as pd

from app.core.config import settings

logger = logging.getLogger("ocr_service")


def run_ocr(model, img, conf_threshold: float | None = None) -> dict:
    """
    Returns:
      {
        "text": str,
        "detections": [{"char":..., "conf":..., "box":[x1,y1,x2,y2], "row_id": int}],
        "latency_ms": int
      }
    """
    t0 = time.time()
    conf_thr = float(conf_threshold if conf_threshold is not None else settings.OCR_CONF_THRESHOLD)
    logger.debug(f"🔍 Running OCR | conf_threshold={conf_thr:.2f}")

    results = model(img)
    det = results.pandas().xyxy[0]  # pandas DataFrame

    if det is None or len(det) == 0:
        logger.warning(f"⚠️  No detections found")
        return {
            "text": "",
            "detections": [],
            "reason": "no_detections",
            "latency_ms": int((time.time() - t0) * 1000),
        }

    det = det.copy()
    det["xc"] = (det["xmin"] + det["xmax"]) / 2
    det["yc"] = (det["ymin"] + det["ymax"]) / 2

    # tách dòng theo median height
    h_med = (det["ymax"] - det["ymin"]).median()
    y_thresh = float(h_med * 0.35) if h_med > 0 else 10.0

    det = det.sort_values(["yc", "xc"])

    row_ids = []
    current_row = 0
    last_y = None
    for y in det["yc"].tolist():
        if last_y is None:
            row_ids.append(current_row)
            last_y = y
            continue
        if abs(y - last_y) > y_thresh:
            current_row += 1
        row_ids.append(current_row)
        last_y = y
    det["row_id"] = row_ids

    det = det.sort_values(["row_id", "xc"])

    det_filtered = det[det["confidence"] >= conf_thr].copy()
    if len(det_filtered) == 0:
        logger.warning(f"⚠️  All {len(det)} detections filtered by confidence threshold")
        return {
            "text": "",
            "detections": [],
            "reason": "all_filtered_by_conf",
            "latency_ms": int((time.time() - t0) * 1000),
        }

    text = ""
    detections = []
    for _, d in det_filtered.iterrows():
        ch = str(d["name"])
        cf = float(d["confidence"])
        box = [float(d["xmin"]), float(d["ymin"]), float(d["xmax"]), float(d["ymax"])]
        rid = int(d["row_id"])
        text += ch
        detections.append({"char": ch, "conf": cf, "box": box, "row_id": rid})

    latency = int((time.time() - t0) * 1000)
    
    return {
        "text": text,
        "detections": detections,
        "latency_ms": latency,
    }
