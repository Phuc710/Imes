pip install -r requirements.txt
# chạy server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
cd C:\Users\Phucx\Desktop\imes\lp-ocr-api
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload