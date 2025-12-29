"""
🔌 Bulk ThingsBoard Provisioning over MQTT
- Provisions N devices using one provisionDeviceKey/Secret
- Processes ONE device at a time to ensure proper response matching  
- Saves results to CSV

Requires:
  pip install paho-mqtt
"""

from __future__ import annotations

import csv
import json
import secrets
import time
from dataclasses import dataclass, field
from typing import List, Optional

import paho.mqtt.client as mqtt

# ======================
# ⚙️ CONFIG
# ======================
HOST = "localhost"
PORT = 1883

PROVISION_KEY = "o75uyb2brk34dvrcu9dh"
PROVISION_SECRET = "r2id29fu6ttstc1lvxn6"

BATCH_PREFIX = "ESP32-LOT2025_12A"
COUNT = 10
QOS = 1
DEVICE_TIMEOUT_SEC = 5  # timeout cho mỗi device
CSV_OUT = "provision_results.csv"

REQUEST_TOPIC = "/provision/request"
RESPONSE_TOPIC = "/provision/response"


# ======================
# 📦 DATA STRUCTURES  
# ======================
@dataclass
class ProvisionResult:
    device_name: str
    status: str = "PENDING"
    token: str = ""
    error_msg: str = ""


def random_hex(nbytes: int = 6) -> str:
    return secrets.token_hex(nbytes).upper()


def make_device_name(i: int) -> str:
    return f"{BATCH_PREFIX}-{random_hex(6)}"


# ======================
# 🔄 PROVISIONER
# ======================
class SequentialProvisioner:
    """Provision one device at a time for reliable response matching."""
    
    def __init__(self) -> None:
        self.connected = False
        self.subscribed = False
        self.current_result: Optional[ProvisionResult] = None
        self.response_received = False
        self.results: List[ProvisionResult] = []

    def on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            self.connected = True
            print("✅ [Connected] MQTT OK")
            client.subscribe(RESPONSE_TOPIC, qos=QOS)
        else:
            print(f"❌ [ERROR] Connect failed rc={rc}")

    def on_subscribe(self, client, userdata, mid, granted_qos, properties=None):
        self.subscribed = True
        print(f"📡 [Subscribed] {RESPONSE_TOPIC}")

    def on_message(self, client, userdata, msg):
        payload_raw = msg.payload.decode(errors="replace")
        
        try:
            data = json.loads(payload_raw)
        except Exception:
            return

        status = data.get("status", "")
        token = data.get("credentialsValue", "") or ""
        err = data.get("errorMsg", "") or ""

        if self.current_result and self.current_result.status == "PENDING":
            if status == "SUCCESS":
                self.current_result.status = "SUCCESS"
                self.current_result.token = token
            else:
                self.current_result.status = "ERROR"
                self.current_result.error_msg = err or f"Status: {status}"
            self.response_received = True

    def provision_one(self, client, device_name: str) -> ProvisionResult:
        """Provision a single device and wait for response."""
        result = ProvisionResult(device_name=device_name)
        self.current_result = result
        self.response_received = False

        payload = {
            "provisionDeviceKey": PROVISION_KEY,
            "provisionDeviceSecret": PROVISION_SECRET,
            "deviceName": device_name,
        }

        client.publish(REQUEST_TOPIC, json.dumps(payload), qos=QOS)

        # Wait for response with timeout
        start = time.time()
        while not self.response_received and (time.time() - start) < DEVICE_TIMEOUT_SEC:
            time.sleep(0.05)

        if not self.response_received:
            result.status = "TIMEOUT"
            result.error_msg = f"No response in {DEVICE_TIMEOUT_SEC}s"

        self.results.append(result)
        return result


def main():
    prov = SequentialProvisioner()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set("provision")
    client.on_connect = prov.on_connect
    client.on_message = prov.on_message
    client.on_subscribe = prov.on_subscribe

    print(f"\n🔌 Connecting to {HOST}:{PORT} ...")
    client.connect(HOST, PORT, 60)
    client.loop_start()

    # Wait connect
    t0 = time.time()
    while not prov.connected and time.time() - t0 < 10:
        time.sleep(0.1)
    if not prov.connected:
        print("❌ [FATAL] MQTT connect timeout.")
        client.loop_stop()
        client.disconnect()
        return

    # Wait subscribe
    while not prov.subscribed and time.time() - t0 < 15:
        time.sleep(0.1)

    print(f"\n🚀 Provisioning {COUNT} devices (one at a time)...\n")
    
    success_count = 0
    error_count = 0
    timeout_count = 0

    for i in range(1, COUNT + 1):
        device_name = make_device_name(i)
        result = prov.provision_one(client, device_name)
        
        if result.status == "SUCCESS":
            icon = "✅"
            success_count += 1
        elif result.status == "ERROR":
            icon = "❌"
            error_count += 1
        else:
            icon = "⏱️"
            timeout_count += 1
        
        # Progress output
        token_preview = result.token[:20] + "..." if len(result.token) > 20 else result.token
        print(f"  {icon} [{i:3d}/{COUNT}] {device_name} → {result.status} {token_preview}")

    client.loop_stop()
    client.disconnect()

    # Summary
    print("\n" + "=" * 50)
    print("📊 SUMMARY")
    print("=" * 50)
    print(f"  ✅ SUCCESS: {success_count}")
    print(f"  ❌ ERROR  : {error_count}")
    print(f"  ⏱️ TIMEOUT: {timeout_count}")
    print("=" * 50)

    # Write CSV
    with open(CSV_OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["deviceName", "status", "token", "errorMsg"])
        for r in prov.results:
            w.writerow([r.device_name, r.status, r.token, r.error_msg])

    print(f"\n💾 Saved: {CSV_OUT}")
    print("🎉 Done!")


if __name__ == "__main__":
    main()
