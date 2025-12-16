import paho.mqtt.client as mqtt
import time
import json
import ssl

# Thay thế bằng Access Token của bạn
ACCESS_TOKEN = "58MBStVQVKENk0PEmoTN"
# Địa chỉ ThingsBoard local của bạn (vì bạn đang chạy Docker trên cổng 1883)
THINGSBOARD_HOST = "192.168.1.61"
THINGSBOARD_PORT = 1883

# --- 1. Hàm Callback khi Kết nối thành công ---
def on_connect(client, userdata, flags, rc):
    """Callback được gọi khi Client kết nối hoặc kết nối lại."""
    if rc == 0:
        print(f"Connected to ThingsBoard MQTT Broker successfully! (rc: {rc})")
        # Đăng ký nhận phản hồi Attributes
        # Topic: v1/devices/me/attributes/response/+
        client.subscribe("v1/devices/me/attributes/response/+")
        print(f"Subscribed to response topic: v1/devices/me/attributes/response/+")

        # Gửi yêu cầu lấy thuộc tính (clientKeys và sharedKeys)
        # Tương đương: client.publish('v1/devices/me/attributes/request/1', '{"clientKeys":"attribute1,attribute2", "sharedKeys":"shared1,shared2"}')
        ATTRIBUTE_REQUEST_ID = "1"
        request_topic = f"v1/devices/me/attributes/request/{ATTRIBUTE_REQUEST_ID}"
        request_payload = json.dumps({"clientKeys": "temperature,humidity", "sharedKeys": "shared1,shared2"})
        
        client.publish(request_topic, request_payload)
        print(f"Published attribute request to topic: {request_topic}")
        print(f"Payload: {request_payload}")
    else:
        print(f"Failed to connect to ThingsBoard, return code: {rc}")

# --- 2. Hàm Callback khi Nhận tin nhắn ---
def on_message(client, userdata, msg):
    """Callback được gọi khi Client nhận được tin nhắn từ Server."""
    print(f"\nResponse Received:")
    print(f"Topic: {msg.topic}")
    print(f"Payload: {msg.payload.decode()}")
    
    # Optional: Ngắt kết nối sau khi nhận được phản hồi đầu tiên
    # client.loop_stop()
    # client.disconnect()

# --- 3. Khởi tạo và Thiết lập MQTT Client ---
client = mqtt.Client()

# Thiết lập Access Token làm Username (như trong code JS)
client.username_pw_set(ACCESS_TOKEN)

# Thiết lập các hàm callback
client.on_connect = on_connect
client.on_message = on_message

# Thực hiện kết nối
print(f"Attempting to connect to {THINGSBOARD_HOST}:{THINGSBOARD_PORT}...")
try:
    # Kết nối đến ThingsBoard
    client.connect(THINGSBOARD_HOST, THINGSBOARD_PORT, 60)
    
    # Bắt đầu vòng lặp xử lý mạng trong một thread riêng
    client.loop_start()

    # Giữ chương trình chạy trong một thời gian để lắng nghe phản hồi
    time.sleep(5) 
    
    # Gửi dữ liệu Telemetry (DEMO: Gửi nhiệt độ sau khi chờ 5 giây)
    print("\n--- Sending Demo Telemetry ---")
    telemetry_topic = "v1/devices/me/telemetry"
    telemetry_data = json.dumps({"temperature": 70, "humidity": 65})
    client.publish(telemetry_topic, telemetry_data, qos=1)
    print(f"Published Telemetry to topic: {telemetry_topic}")
    print(f"Payload: {telemetry_data}")
    
    time.sleep(2) # Cho thời gian gửi và nhận
    
    # Dừng vòng lặp mạng và ngắt kết nối
    client.loop_stop()
    client.disconnect()

except Exception as e:
    print(f"An error occurred: {e}")

print("Script finished.")