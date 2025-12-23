
import paho.mqtt.client as mqtt
import json
import time
import random
from datetime import datetime

# ===== CẤU HÌNH =====
GATEWAY_HOST = "192.168.1.71"
GATEWAY_PORT = 18883
DEVICE_NAME = "ESP32_Test_02"
TOPIC = f"sensor/{DEVICE_NAME}/data"

# ===== CALLBACK (FIX LỖI COMPATIBILITY) =====
def on_connect(client, userdata, flags, reason_code, properties=None):
    """Callback khi kết nối - Compatible với paho-mqtt 2.x"""
    if reason_code == 0:
        print("✅ KẾT NỐI THÀNH CÔNG!\n")
    else:
        print(f"❌ KẾT NỐI THẤT BẠI! Code: {reason_code}\n")

def on_publish(client, userdata, mid, reason_code=None, properties=None):
    """Callback khi publish - Compatible với paho-mqtt 2.x"""
    pass  # Không cần print mỗi lần publish

# ===== HEADER =====
print("\n" + "="*70)
print("📡 MQTT DATA SENDER - THINGSBOARD GATEWAY")
print("="*70)
print(f"🌐 Broker  : {GATEWAY_HOST}:{GATEWAY_PORT}")
print(f"📱 Device  : {DEVICE_NAME}")
print(f"📤 Topic   : {TOPIC}")
print("="*70 + "\n")

# ===== TẠO CLIENT =====
client = mqtt.Client(
    client_id=DEVICE_NAME,
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2,  # Fix deprecation
    protocol=mqtt.MQTTv5
)
client.on_connect = on_connect
client.on_publish = on_publish

# ===== KẾT NỐI =====
print("🔄 Đang kết nối...\n")
try:
    client.connect(GATEWAY_HOST, GATEWAY_PORT, 60)
    client.loop_start()
    time.sleep(2)
    
    # ===== HEADER BẢNG DỮ LIỆU =====
    print("┌─────────────────────┬──────────────┬──────────────┬────────┐")
    print("│ Timestamp           │ Temperature  │ Humidity     │ Status │")
    print("├─────────────────────┼──────────────┼──────────────┼────────┤")
    
    # ===== GỬI DỮ LIỆU =====
    for i in range(5):
        # Tạo data
        temp = round(20 + random.uniform(0, 10), 2)
        hum = round(50 + random.uniform(0, 30), 2)
        
        data = {
            "deviceName": DEVICE_NAME,
            "deviceType": "sensor",
            "temperature": temp,
            "humidity": hum
        }
        
        # Lấy timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Publish
        payload = json.dumps(data)
        result = client.publish(TOPIC, payload, qos=1)
        
        # Hiển thị dạng bảng
        status = "✅ OK" if result.rc == 0 else "❌ FAIL"
        print(f"│ {timestamp} │ {temp:>10.2f}°C │ {hum:>10.2f}%  │ {status:^6} │")
        
        time.sleep(2)
    
    # ===== FOOTER BẢNG =====
    print("└─────────────────────┴──────────────┴──────────────┴────────┘")
    print("\n✅ ĐÃ GỬI XONG 5 MESSAGES!\n")
    
    time.sleep(1)
    
except KeyboardInterrupt:
    print("\n⚠️  Dừng bởi người dùng\n")
except Exception as e:
    print(f"\n❌ LỖI: {e}\n")
finally:
    client.loop_stop()
    client.disconnect()

# ===== HƯỚNG DẪN KIỂM TRA =====
print("="*70)
print("👉 KIỂM TRA DỮ LIỆU TRÊN THINGSBOARD:")
print("="*70)
print("1. Mở: http://localhost:8080")
print("2. Vào: Entities → Devices → ESP32_Test_01")
print("3. Tab: Latest telemetry")
print("4. Xem: temperature, humidity với timestamp")
print("="*70 + "\n")
