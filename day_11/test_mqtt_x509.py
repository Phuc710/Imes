#!/usr/bin/env python3
"""
Test MQTT SSL connection with X.509 client certificate
Giống như ESP32 code - simplified version
"""

import ssl
import time
import json
import random
import paho.mqtt.client as mqtt

# ===== CONFIG =====
TB_HOST = "192.168.1.95"
TB_PORT = 8883

# Certificates
CA_CERT = "tb_ssl/rootCert.pem"
CLIENT_CERT = "esp32/certs/chain.pem"
CLIENT_KEY = "esp32/certs/deviceKey.pem"

# Device name
DEVICE_NAME = "A842E3578AD4"  # Clean MAC only

# ===== CALLBACKS =====
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("   ✅ MQTT OK\n")
    else:
        errors = {1: "BAD_PROTOCOL", 2: "BAD_CLIENT_ID", 3: "UNAVAILABLE", 
                  4: "BAD_CREDENTIALS", 5: "UNAUTHORIZED"}
        print(f"   ❌ MQTT lỗi: {errors.get(rc, f'UNKNOWN ({rc})')}\n")

def on_publish(client, userdata, mid):
    print(f"   ✅ Published (mid: {mid})")

# ===== MAIN =====
print("=== Python MQTT X.509 Test ===\n")

# Create client
client = mqtt.Client(client_id=DEVICE_NAME)
client.on_connect = on_connect
client.on_publish = on_publish

# SSL Setup
print("🔐 Kết nối MQTT SSL...")
print(f"   Device: {DEVICE_NAME}")
print(f"   Server: {TB_HOST}:{TB_PORT}")

try:
    print("   📜 Load cert...")
    print("   🔑 Load key...")
    
    client.tls_set(
        ca_certs=CA_CERT,            # Root CA dùng để verify server
        certfile=CLIENT_CERT,        # Certificate của Device
        keyfile=CLIENT_KEY,          # Private Key của Device
        cert_reqs=ssl.CERT_NONE,     # Dùng CERT_NONE để tránh lỗi "self-signed certificate" khi test
        tls_version=ssl.PROTOCOL_TLS
    )
    
    # Bỏ qua kiểm tra Hostname (giống ESP32 không check hostname)
    client.tls_insecure_set(True)
    
    print("   ✅ SSL Configured")
    
    client.connect(TB_HOST, TB_PORT, keepalive=60)
    print("   🤝 SSL handshake...")
    print("   ✅ SSL OK")
    print("   🔌 MQTT connect...")
    
    client.loop_start()
    time.sleep(2)
    
    # Publish data
    print("\n📤 Publishing telemetry...")
    for i in range(5):
        data = {"temp": random.randint(20, 35), "hum": random.randint(40, 80)}
        payload = json.dumps(data)
        print(f"📤 {payload}")
        client.publish("v1/devices/me/telemetry", payload)
        time.sleep(10)
    
    client.loop_stop()
    client.disconnect()
    print("\n✅ Test completed!")
    
except FileNotFoundError as e:
    print(f"   ❌ Certificate file not found: {e}")
except Exception as e:
    print(f"   ❌ Error: {e}")
