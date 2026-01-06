"""
Test MQTT with correct X.509 topic
ThingsBoard X.509 devices use different topic format
"""

import ssl
import paho.mqtt.client as mqtt
import time
import json

# Configuration
THINGSBOARD_HOST = "192.168.1.95"
THINGSBOARD_PORT = 8883
DEVICE_NAME = "A842E3578AD4"

# Certificate paths
CA_CERT = "certs/root_ca.pem"
CLIENT_CERT = "certs/A842E3578AD4.crt"
CLIENT_KEY = "certs/A842E3578AD4.key"

# MQTT topics for X.509 devices
TELEMETRY_TOPIC = "v1/devices/me/telemetry"
ATTRIBUTES_TOPIC = "v1/devices/me/attributes"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"✅ Connected successfully!")
        print(f"   Session present: {flags.get('session present', 0)}")
        
        # Subscribe to attribute updates
        client.subscribe("v1/devices/me/attributes/response/+")
        client.subscribe("v1/devices/me/rpc/request/+")
        print("📬 Subscribed to topics")
        
    else:
        print(f"❌ Connection failed: rc={rc}")

def on_disconnect(client, userdata, rc):
    if rc == 0:
        print("👋 Disconnected cleanly")
    else:
        print(f"⚠️  Unexpected disconnect: rc={rc}")
        error_codes = {
            1: "Incorrect protocol version",
            2: "Invalid client identifier",
            3: "Server unavailable",
            4: "Bad username or password",
            5: "Not authorized",
            7: "No connection (credentials issue)"
        }
        print(f"   Reason: {error_codes.get(rc, 'Unknown')}")

def on_message(client, userdata, msg):
    print(f"📨 [{msg.topic}]: {msg.payload.decode()}")

def on_publish(client, userdata, mid):
    print(f"   ✓ Published (mid={mid})")

def on_subscribe(client, userdata, mid, granted_qos):
    print(f"   ✓ Subscribed (mid={mid}, qos={granted_qos})")

def main():
    print("=" * 70)
    print("🔐 ThingsBoard X.509 MQTT Test (Fixed)")
    print("=" * 70)
    print(f"\n📋 Config: {THINGSBOARD_HOST}:{THINGSBOARD_PORT}")
    print(f"📱 Device: {DEVICE_NAME}")
    print("=" * 70)
    
    # Create client
    client = mqtt.Client(client_id=DEVICE_NAME, protocol=mqtt.MQTTv311)
    
    # Set callbacks
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    client.on_publish = on_publish
    client.on_subscribe = on_subscribe
    
    # Configure TLS
    print("\n🔐 Loading certificates...")
    client.tls_set(
        ca_certs=CA_CERT,
        certfile=CLIENT_CERT,
        keyfile=CLIENT_KEY,
        cert_reqs=ssl.CERT_REQUIRED,
        tls_version=ssl.PROTOCOL_TLSv1_2
    )
    print("✅ Certificates loaded")
    
    # Connect
    print(f"\n🔌 Connecting...")
    try:
        client.connect(THINGSBOARD_HOST, THINGSBOARD_PORT, keepalive=60)
        client.loop_start()
        
        # Wait for connection
        time.sleep(2)
        
        if client.is_connected():
            print("\n📤 Sending telemetry...")
            
            # Send telemetry
            for i in range(5):
                payload = json.dumps({
                    "temperature": 25.0 + i,
                    "humidity": 60 + i,
                    "test_number": i + 1
                })
                
                result = client.publish(TELEMETRY_TOPIC, payload, qos=1)
                print(f"   [{i+1}] {payload}", end="")
                
                if result.rc != mqtt.MQTT_ERR_SUCCESS:
                    print(f" ❌ Failed: {result.rc}")
                
                time.sleep(2)
            
            # Send attributes
            print("\n📤 Sending attributes...")
            attrs = json.dumps({
                "firmware_version": "1.0.0",
                "mac_address": DEVICE_NAME
            })
            client.publish(ATTRIBUTES_TOPIC, attrs, qos=1)
            print(f"   {attrs}")
            
            # Keep alive
            print("\n⏳ Keeping connection alive for 10 seconds...")
            time.sleep(10)
            
        else:
            print("❌ Failed to connect")
        
        # Disconnect
        print("\n👋 Disconnecting...")
        client.loop_stop()
        client.disconnect()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("✨ Test complete!")
    print("=" * 70)

if __name__ == "__main__":
    main()
