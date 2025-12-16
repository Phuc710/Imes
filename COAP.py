import paho.mqtt.client as mqtt
import json
import time

# Cấu hình
THINGSBOARD_HOST = "192.168.1.61"
ACCESS_TOKEN = "58MBStVQVKENk0PEmoTN"

# Callback khi kết nối
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✓ Connected to ThingsBoard!")
    else:
        print(f"✗ Connection failed with code {rc}")

# Callback khi gửi thành công
def on_publish(client, userdata, mid):
    print(f"✓ Message {mid} published")

# Tạo MQTT client
client = mqtt.Client()
client.username_pw_set(ACCESS_TOKEN)
client.on_connect = on_connect
client.on_publish = on_publish

print(f"Connecting to {THINGSBOARD_HOST}:1883...")
client.connect(THINGSBOARD_HOST, 1883, 60)
client.loop_start()

time.sleep(2)

# Gửi telemetry
print("\nSending telemetry...")
telemetry = {"temperature": 25, "humidity": 100}
result = client.publish('v1/devices/me/telemetry', json.dumps(telemetry), 1)
print(f"Data sent: {telemetry}")

time.sleep(2)

# Gửi attributes
print("\nSending attributes...")
attributes = {"model": "ESP32", "firmware": "v1.0"}
result = client.publish('v1/devices/me/attributes', json.dumps(attributes), 1)
print(f"Attributes sent: {attributes}")

time.sleep(2)

client.loop_stop()
client.disconnect()
print("\n✓ Test completed!")