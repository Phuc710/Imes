from flask import Flask, request
import os, time

app = Flask(__name__)

SAVE_DIR = "images"
os.makedirs(SAVE_DIR, exist_ok=True)

@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return {"error": "no file field"}, 400

    f = request.files["file"]
    if f.filename == "":
        return {"error": "empty filename"}, 400

    name = f"{int(time.time())}.jpg"
    path = os.path.join(SAVE_DIR, name)
    f.save(path)

    print("Saved:", path)
    return {"status": "ok", "file": name}, 200

@app.route("/")
def index():
    return "ESP32 LOCAL SERVER OK"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
