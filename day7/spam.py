import asyncio
import aiohttp
import time
import os
import random
from io import BytesIO
from PIL import Image
import uuid

# Config
URL = "http://103.249.117.210:3340/ocr/kafka?camera_id=2&save_img=false"
NUM_CONCURRENT = 5  # CHỈ 5 LUỒNG ĐỒNG THỜI
DELAY_BETWEEN = 0.1  # delay nhỏ giữa request để tránh quá tải (giảm xuống 0 nếu muốn nhanh hơn)
FOLDER_IMAGES = "images"

USER_AGENTS = [
    "Hikvision/1.0 (Camera)",
    "Dahua/2.0",
    "CameraClient/1.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

def random_user_agent():
    return random.choice(USER_AGENTS)

def generate_fake_image():
    width = random.randint(640, 1280)
    height = random.randint(480, 720)
    img = Image.new('RGB', (width, height), color=(random.randint(0,255), random.randint(0,255), random.randint(0,255)))
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=80)
    buffer.seek(0)
    return buffer

async def get_random_image():
    if os.path.exists(FOLDER_IMAGES) and os.listdir(FOLDER_IMAGES):
        files = [f for f in os.listdir(FOLDER_IMAGES) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        if files:
            file_path = os.path.join(FOLDER_IMAGES, random.choice(files))
            with open(file_path, 'rb') as f:
                return BytesIO(f.read()), f"image_{uuid.uuid4().hex}.jpg"
    buffer = generate_fake_image()
    return buffer, f"fake_{uuid.uuid4().hex}.jpg"

async def upload_image(session, counter):
    while True:
        try:
            start_req = time.time()
            img_buffer, filename = await get_random_image()
            
            form = aiohttp.FormData()
            form.add_field('file', img_buffer, filename=filename, content_type='image/jpeg')
            form.add_field('timestamp', str(time.time()))
            
            headers = {
                "User-Agent": random_user_agent(),
                "Connection": "keep-alive",
            }

            async with session.post(URL, data=form, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                status = resp.status
                response_text = await resp.text()
                elapsed = time.time() - start_req
                counter[0] += 1
                
                # Log chi tiết (như log mẫu của mày)
                print(f"[{counter[0]:4d}] {status} | {elapsed:.3f}s | "
                      f"UA: {headers['User-Agent'][:30]}... | "
                      f"Resp: {response_text[:120]}{'...' if len(response_text) > 120 else ''}")

        except Exception as e:
            counter[0] += 1
            print(f"[{counter[0]:4d}] ERROR | {str(e)[:100]}")
        
        await asyncio.sleep(DELAY_BETWEEN)  # delay giữa các request

async def main():
    counter = [0]
    start_time = time.time()

    print(f"Bắt đầu test với 5 luồng đồng thời...")
    print(f"Delay giữa request: {DELAY_BETWEEN}s")
    print("Nhấn Ctrl+C để dừng\n")

    connector = aiohttp.TCPConnector(limit=NUM_CONCURRENT * 2)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [upload_image(session, counter) for _ in range(NUM_CONCURRENT)]
        await asyncio.gather(*tasks, return_exceptions=True)

    elapsed = time.time() - start_time
    print(f"\n=== KẾT THÚC ===")
    print(f"Tổng request: {counter[0]}")
    print(f"Tốc độ trung bình: {counter[0]/elapsed:.1f} req/s")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDừng spam...")