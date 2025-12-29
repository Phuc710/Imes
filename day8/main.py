from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
import hashlib
import os

app = FastAPI()

FW_PATH = "./firmware/esp32.bin"

def calc_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest()

@app.get("/fw/info")
def fw_info():
    if not os.path.exists(FW_PATH):
        return JSONResponse({"error": "firmware not found"}, status_code=404)

    sha = calc_sha256(FW_PATH)
    size = os.path.getsize(FW_PATH)
    return {
        "ver": "2",
        "sha256": sha,
        "size": size,
        "url": "http://192.168.1.95:8000/fw/esp32.bin"
    }

@app.get("/fw/esp32.bin")
def fw_bin():
    if not os.path.exists(FW_PATH):
        return JSONResponse({"error": "firmware not found"}, status_code=404)

    # FileResponse sẽ tự hỗ trợ streaming (chunked OK)
    return FileResponse(FW_PATH, media_type="application/octet-stream", filename="esp32.bin")
