#include <WiFi.h>
#include <WiFiManager.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include "../certs/esp32_certs.h"

// ===== CONFIGURATION =====
const char* TB_HOST = "192.168.1.95";
const int   TB_PORT = 8883;

// ===== HARDWARE =====
const int BTN_PIN = 0;              // BOOT button GPIO0
const uint32_t HOLD_MS = 3000;      // Hold 3s to reset WiFi

// ===== GLOBALS =====
WiFiClientSecure espClient;
PubSubClient mqtt(espClient);
String deviceName;
bool mqttConnected = false;
uint32_t lastReconnect = 0;
uint32_t lastSend = 0;

// ===== GET DEVICE NAME FROM MAC =====
String macToName() {
  uint8_t mac[6];
  WiFi.macAddress(mac);
  char s[13];
  snprintf(s, sizeof(s), "%02X%02X%02X%02X%02X%02X",
           mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
  return String(s);
}

// ===== RESET WIFI =====
void resetWiFi() {
  Serial.println("🗑️ Resetting WiFi...");
  WiFi.disconnect(true, true);
  delay(200);
  ESP.restart();
}

// ===== CONNECT WIFI =====
void connectWiFi() {
  WiFiManager wm;
  wm.setConfigPortalTimeout(180);
  
  Serial.println("📡 Connecting WiFi...");
  if (!wm.autoConnect("ESP32_X509", "12345678")) {
    Serial.println("❌ WiFi failed");
    ESP.restart();
  }
  
  Serial.print("✅ WiFi: ");
  Serial.println(WiFi.localIP());

  // Sync NTP for certificate validation
  Serial.println("🕒 Syncing time...");
  configTime(7 * 3600, 0, "pool.ntp.org", "time.nist.gov");
  
  struct tm timeinfo;
  int retry = 0;
  while (!getLocalTime(&timeinfo) && retry < 20) {
    Serial.print(".");
    delay(500);
    retry++;
  }
  
  if (retry >= 20) {
    Serial.println("\n❌ NTP failed!");
    ESP.restart();
  }
  
  Serial.println();
  Serial.print("✅ Time: ");
  Serial.println(&timeinfo, "%Y-%m-%d %H:%M:%S");
}

// ===== MQTT RECONNECT =====
void mqttReconnect() {
  mqttConnected = false;
  
  Serial.println("\n🔐 MQTT SSL X.509 Auto-Provisioning");
  Serial.println("   Device: " + deviceName);
  Serial.println("   Server: " + String(TB_HOST) + ":" + String(TB_PORT));
  
  espClient.stop();
  delay(100);
  
  // Load certificates
  espClient.setInsecure();  // Skip hostname check (using IP)
  espClient.setCertificate(device_cert_chain);
  espClient.setPrivateKey(device_key);
  Serial.println("   ✅ Certs loaded");
  
  // SSL handshake
  Serial.println("   🤝 SSL handshake...");
  if (!espClient.connect(TB_HOST, TB_PORT)) {
    Serial.println("   ❌ SSL FAILED");
    return;
  }
  Serial.println("   ✅ SSL OK");
  
  // MQTT connect
  // Username MUST match certificate CN!
  Serial.println("   🔌 MQTT connect...");
  if (mqtt.connect(deviceName.c_str(), deviceName.c_str(), "")) {
    mqttConnected = true;
    Serial.println("   ✅ MQTT OK");
    Serial.println("   🎉 Auto-provisioned!\n");
  } else {
    Serial.print("   ❌ Error: ");
    Serial.println(mqtt.state());
  }
}

// ===== SETUP =====
void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("\n=== ESP32 X.509 Auto-Provision ===");
  
  pinMode(BTN_PIN, INPUT_PULLUP);
  connectWiFi();
  
  deviceName = macToName();
  Serial.println("Device: " + deviceName);
  
  mqtt.setServer(TB_HOST, TB_PORT);
  mqtt.setBufferSize(2048);
}

// ===== LOOP =====
void loop() {
  // Hold BOOT 3s to reset WiFi
  static uint32_t btnMs = 0;
  if (digitalRead(BTN_PIN) == LOW) {
    if (btnMs == 0) btnMs = millis();
    if (millis() - btnMs > HOLD_MS) resetWiFi();
  } else {
    btnMs = 0;
  }

  // MQTT maintain
  if (!mqtt.connected() && millis() - lastReconnect > 5000) {
    lastReconnect = millis();
    mqttReconnect();
  }
  mqtt.loop();

  // Send telemetry every 10s
  if (mqttConnected && millis() - lastSend > 10000) {
    lastSend = millis();
    
    DynamicJsonDocument d(64);
    d["temp"] = random(20, 35);
    d["hum"] = random(40, 80);
    
    char buf[64];
    serializeJson(d, buf);
    
    Serial.print("📤 [" + deviceName + "] ");
    Serial.println(buf);
    
    mqtt.publish("v1/devices/me/telemetry", buf);
  }
}
