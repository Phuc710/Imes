/*
 * 🔌 ESP32 ThingsBoard Auto Provisioning
 * - Tự động đăng ký với ThingsBoard khi nạp code
 * - Lưu token vào EEPROM sau khi provision thành công
 * - Gửi telemetry định kỳ
 * 
 * Yêu cầu:
 *   - Board: ESP32
 *   - Library: PubSubClient, ArduinoJson
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <EEPROM.h>

// ======================
// ⚙️ CONFIG - THAY ĐỔI THEO HỆ THỐNG CỦA BẠN
// ======================
const char* WIFI_SSID = "iMES";
const char* WIFI_PASSWORD = "Imes@2025";

const char* THINGSBOARD_HOST = "192.168.1.95";  // IP của ThingsBoard server
const int THINGSBOARD_PORT = 1883;

// Provision keys từ Device Profile trên ThingsBoard
const char* PROVISION_DEVICE_KEY = "aqtz9husob3m1gxcexyj";
const char* PROVISION_DEVICE_SECRET = "f24l3p2xfqdjmq95m1os";

// ======================
// 📌 CONSTANTS
// ======================
#define EEPROM_SIZE 512
#define TOKEN_ADDR 0
#define TOKEN_FLAG_ADDR 100
#define TOKEN_FLAG_VALUE 0xAB

const char* PROVISION_REQUEST_TOPIC = "/provision/request";
const char* PROVISION_RESPONSE_TOPIC = "/provision/response";
const char* TELEMETRY_TOPIC = "v1/devices/me/telemetry";

// ======================
// 🔧 GLOBAL VARIABLES
// ======================
WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);

char deviceToken[64] = "";
bool isProvisioned = false;
bool provisionResponseReceived = false;
unsigned long lastTelemetryTime = 0;
const unsigned long TELEMETRY_INTERVAL = 5000;  // 5 giây gửi 1 lần

// ======================
// 📡 WIFI FUNCTIONS
// ======================
void setupWiFi() {
  Serial.print("🔌 Connecting to WiFi: ");
  Serial.println(WIFI_SSID);
  
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✅ WiFi Connected!");
    Serial.print("📍 IP Address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n❌ WiFi Connection Failed!");
  }
}

// ======================
// 💾 EEPROM FUNCTIONS
// ======================
void saveToken(const char* token) {
  EEPROM.write(TOKEN_FLAG_ADDR, TOKEN_FLAG_VALUE);
  for (int i = 0; i < strlen(token); i++) {
    EEPROM.write(TOKEN_ADDR + i, token[i]);
  }
  EEPROM.write(TOKEN_ADDR + strlen(token), '\0');
  EEPROM.commit();
  Serial.println("💾 Token saved to EEPROM");
}

bool loadToken() {
  if (EEPROM.read(TOKEN_FLAG_ADDR) != TOKEN_FLAG_VALUE) {
    return false;
  }
  
  for (int i = 0; i < 64; i++) {
    deviceToken[i] = EEPROM.read(TOKEN_ADDR + i);
    if (deviceToken[i] == '\0') break;
  }
  
  if (strlen(deviceToken) > 0) {
    Serial.print("📖 Token loaded from EEPROM: ");
    Serial.println(deviceToken);
    return true;
  }
  return false;
}

void clearToken() {
  EEPROM.write(TOKEN_FLAG_ADDR, 0);
  EEPROM.commit();
  Serial.println("🗑️ Token cleared from EEPROM");
}

// ======================
// 📨 MQTT CALLBACKS
// ======================
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  Serial.print("📩 Message received on topic: ");
  Serial.println(topic);
  
  // Parse JSON response
  StaticJsonDocument<256> doc;
  DeserializationError error = deserializeJson(doc, payload, length);
  
  if (error) {
    Serial.println("❌ JSON parse error");
    return;
  }
  
  // Check if this is provision response
  if (String(topic) == PROVISION_RESPONSE_TOPIC) {
    const char* status = doc["status"];
    
    if (strcmp(status, "SUCCESS") == 0) {
      const char* token = doc["credentialsValue"];
      strcpy(deviceToken, token);
      saveToken(token);
      isProvisioned = true;
      provisionResponseReceived = true;
      
      Serial.println("✅ Provision SUCCESS!");
      Serial.print("🔑 Token: ");
      Serial.println(deviceToken);
    } else {
      const char* errorMsg = doc["errorMsg"] | "Unknown error";
      Serial.print("❌ Provision FAILED: ");
      Serial.println(errorMsg);
      provisionResponseReceived = true;
    }
  }
}

// ======================
// 🔄 PROVISIONING
// ======================
bool provisionDevice() {
  Serial.println("\n🚀 Starting device provisioning...");
  
  // Connect with "provision" username
  mqtt.setServer(THINGSBOARD_HOST, THINGSBOARD_PORT);
  mqtt.setCallback(mqttCallback);
  
  String clientId = "ESP32_" + String(ESP.getEfuseMac(), HEX);
  
  if (!mqtt.connect(clientId.c_str(), "provision", NULL)) {
    Serial.println("❌ MQTT connect failed for provisioning");
    return false;
  }
  
  Serial.println("✅ Connected to MQTT (provisioning mode)");
  
  // Subscribe to provision response
  mqtt.subscribe(PROVISION_RESPONSE_TOPIC);
  Serial.println("📡 Subscribed to provision response");
  
  // Create provision request
  StaticJsonDocument<256> doc;
  doc["provisionDeviceKey"] = PROVISION_DEVICE_KEY;
  doc["provisionDeviceSecret"] = PROVISION_DEVICE_SECRET;
  doc["deviceName"] = clientId;  // Use MAC as device name
  
  char jsonBuffer[256];
  serializeJson(doc, jsonBuffer);
  
  // Publish provision request
  Serial.print("📤 Sending provision request: ");
  Serial.println(jsonBuffer);
  mqtt.publish(PROVISION_REQUEST_TOPIC, jsonBuffer);
  
  // Wait for response
  unsigned long startTime = millis();
  while (!provisionResponseReceived && (millis() - startTime) < 10000) {
    mqtt.loop();
    delay(100);
  }
  
  mqtt.disconnect();
  
  if (isProvisioned) {
    Serial.println("🎉 Device provisioned successfully!");
    return true;
  } else {
    Serial.println("⏱️ Provision timeout or failed");
    return false;
  }
}

// ======================
// 📊 TELEMETRY
// ======================
bool connectWithToken() {
  if (!mqtt.connected()) {
    String clientId = "ESP32_" + String(ESP.getEfuseMac(), HEX);
    
    if (mqtt.connect(clientId.c_str(), deviceToken, NULL)) {
      Serial.println("✅ Connected to ThingsBoard with token");
      return true;
    } else {
      Serial.println("❌ MQTT connect failed with token");
      return false;
    }
  }
  return true;
}

void sendTelemetry() {
  if (!connectWithToken()) return;
  
  // Create telemetry data
  StaticJsonDocument<128> doc;
  doc["temperature"] = random(200, 350) / 10.0;  // 20.0 - 35.0
  doc["humidity"] = random(400, 800) / 10.0;     // 40.0 - 80.0
  doc["status"] = "online";
  
  char jsonBuffer[128];
  serializeJson(doc, jsonBuffer);
  
  if (mqtt.publish(TELEMETRY_TOPIC, jsonBuffer)) {
    Serial.print("📤 Telemetry sent: ");
    Serial.println(jsonBuffer);
  } else {
    Serial.println("❌ Telemetry send failed");
  }
}

// ======================
// 🚀 SETUP & LOOP
// ======================
void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n");
  Serial.println("============================================");
  Serial.println("   🔌 ESP32 ThingsBoard Auto Provisioning");
  Serial.println("============================================");
  
  EEPROM.begin(EEPROM_SIZE);
  
  // Connect to WiFi
  setupWiFi();
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("❌ Cannot proceed without WiFi");
    return;
  }
  
  // Check if already provisioned
  if (loadToken()) {
    Serial.println("📌 Device already provisioned!");
    isProvisioned = true;
  } else {
    Serial.println("📌 Device not provisioned, starting provisioning...");
    provisionDevice();
  }
  
  if (isProvisioned) {
    // Reconnect with device token
    mqtt.setServer(THINGSBOARD_HOST, THINGSBOARD_PORT);
    mqtt.setCallback(mqttCallback);
  }
}

void loop() {
  if (!isProvisioned) {
    delay(5000);
    return;
  }
  
  mqtt.loop();
  
  // Send telemetry periodically
  if (millis() - lastTelemetryTime > TELEMETRY_INTERVAL) {
    sendTelemetry();
    lastTelemetryTime = millis();
  }
}

// ======================
// 🔧 UTILITY: Clear token (uncomment in setup() to reset)
// ======================
// void resetDevice() {
//   clearToken();
//   ESP.restart();
// }
