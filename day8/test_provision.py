"""
Simple ThingsBoard Provisioning Test Script
Tests if provisioning is working via MQTT
"""

import paho.mqtt.client as mqtt
import json
import time

# Configuration
HOST = "localhost"
PORT = 1883
PROVISION_KEY = "aqtz9husob3m1gxcexyj"
PROVISION_SECRET = "f24l3p2xfqdjmq95m1os"
DEVICE_NAME = "test_simple_device_03"

# Provisioning topics
REQUEST_TOPIC = "/provision/request"
RESPONSE_TOPIC = "/provision/response"

received_response = False

def on_connect(client, userdata, flags, rc, properties=None):
    print(f"[Connected] rc={rc}")
    if rc == 0:
        # Subscribe to response topic
        client.subscribe(RESPONSE_TOPIC)
        print(f"[Subscribed] {RESPONSE_TOPIC}")
        
        # Send provision request
        payload = {
            "provisionDeviceKey": PROVISION_KEY,
            "provisionDeviceSecret": PROVISION_SECRET,
            "deviceName": DEVICE_NAME
        }
        print(f"[Sending] Topic: {REQUEST_TOPIC}")
        print(f"[Sending] Payload: {json.dumps(payload)}")
        client.publish(REQUEST_TOPIC, json.dumps(payload))
    else:
        print(f"[ERROR] Connection failed: {rc}")

def on_message(client, userdata, msg):
    global received_response
    print(f"\n[RECEIVED MESSAGE]")
    print(f"  Topic: {msg.topic}")
    print(f"  Payload: {msg.payload.decode()}")
    
    try:
        data = json.loads(msg.payload.decode())
        if data.get("status") == "SUCCESS":
            print(f"\n✅ PROVISION SUCCESS!")
            print(f"   Token: {data.get('credentialsValue')}")
            received_response = True
        elif "errorMsg" in data:
            print(f"\n❌ PROVISION ERROR: {data.get('errorMsg')}")
            received_response = True
    except:
        print("  (Could not parse as JSON)")

def on_subscribe(client, userdata, mid, granted_qos, properties=None):
    print(f"[Subscribed] mid={mid}, qos={granted_qos}")

# Create client with callback API v2
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.username_pw_set("provision")  # Important!
client.on_connect = on_connect
client.on_message = on_message
client.on_subscribe = on_subscribe

print(f"Connecting to {HOST}:{PORT}...")
client.connect(HOST, PORT, 60)

# Run loop with timeout
client.loop_start()
start = time.time()
while time.time() - start < 15:
    if received_response:
        break
    time.sleep(0.5)

if not received_response:
    print("\n⚠️ TIMEOUT: No response received after 15 seconds")
    print("   This means ThingsBoard is not processing provisioning requests.")
    print("   Possible causes:")
    print("   1. Device Profile not saved properly")
    print("   2. ThingsBoard needs restart")
    print("   3. Wrong provision key/secret")

client.loop_stop()
client.disconnect()
