

import csv
import json
import time
import random
from pathlib import Path

import paho.mqtt.client as mqtt

# ======================
# ⚙️ CONFIG
# ======================
HOST = "localhost"
PORT = 1883
CSV_FILE = "provision_results.csv"
TELEMETRY_TOPIC = "v1/devices/me/telemetry"


def activate_device(token: str, device_name: str) -> bool:
    """Connect with device token and send telemetry to activate it."""
    activated = False
    connected_flag = {"value": False}
    
    def on_connect(client, userdata, flags, rc, properties=None):
        if rc == 0:
            connected_flag["value"] = True
        
    def on_publish(client, userdata, mid, rc=None, properties=None):
        pass
    
    try:
        dev_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        dev_client.username_pw_set(token)
        dev_client.on_connect = on_connect
        dev_client.on_publish = on_publish
        
        dev_client.connect(HOST, PORT, 60)
        dev_client.loop_start()
        
        # Wait for connection
        start = time.time()
        while not connected_flag["value"] and (time.time() - start) < 3:
            time.sleep(0.05)
        
        if connected_flag["value"]:
            # Send telemetry to activate device
            telemetry = {
                "temperature": round(random.uniform(20, 30), 1),
                "humidity": round(random.uniform(40, 70), 1),
                "status": "online",
                "firmware": "1.0.0"
            }
            result = dev_client.publish(TELEMETRY_TOPIC, json.dumps(telemetry), qos=1)
            result.wait_for_publish(timeout=2)
            activated = True
            
        dev_client.loop_stop()
        dev_client.disconnect()
        
    except Exception as e:
        pass
    
    return activated


def main():
    csv_path = Path(CSV_FILE)
    
    if not csv_path.exists():
        print(f"❌ File not found: {CSV_FILE}")
        return
    
    # Read CSV
    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    if not rows:
        print("❌ No devices found in CSV")
        return
    
    print(f"\nActivating {len(rows)} devices from {CSV_FILE}...\n")

    activated_count = 0
    failed_count = 0
    
    for i, row in enumerate(rows, 1):
        device_name = row.get("deviceName", "Unknown")
        token = row.get("token", "")
        status = row.get("status", "")
        
        # Skip if no token or already has error
        if not token or status != "SUCCESS":
            print(f"  ⏭️ [{i:3d}/{len(rows)}] {device_name} → SKIPPED (no token or error)")
            row["activated"] = "False"
            failed_count += 1
            continue
        
        # Activate device
        success = activate_device(token, device_name)
        row["activated"] = str(success)
        
        if success:
            print(f"  🟢 [{i:3d}/{len(rows)}] {device_name} → ACTIVATED")
            activated_count += 1
        else:
            print(f"  ❌ [{i:3d}/{len(rows)}] {device_name} → FAILED")
            failed_count += 1
    
    # Write updated CSV
    fieldnames = ["deviceName", "status", "token", "activated", "errorMsg"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 SUMMARY")
    print("=" * 50)
    print(f"  🟢 ACTIVATED: {activated_count}")
    print(f"  ❌ FAILED   : {failed_count}")
    print("=" * 50)
    print(f"\n💾 Updated: {CSV_FILE}")
    print("🎉 Done!")


if __name__ == "__main__":
    main()
