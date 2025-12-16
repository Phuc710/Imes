import requests

url = "http://127.0.0.1:8000/v1/ocr?conf_threshold=0.5"
files = {"file": open(r"C:\Users\Phucx\Desktop\imes\lp-ocr-api\1.jpg", "rb")}
r = requests.post(url, files=files, timeout=60)
print(r.status_code)
print(r.json())
