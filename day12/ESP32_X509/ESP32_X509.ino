/*
 * ESP32 X.509 Auto-Provisioning with OTA Update Support
 * 
 * Features:
 * - MQTT over TLS/SSL with X.509 client certificates
 * - ThingsBoard auto-provisioning
 * - OTA firmware updates via HTTP
 * - Firmware version reporting
 */

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <HTTPUpdate.h>
#include <Update.h>
#include <ArduinoJson.h>
#include "esp32_certs.h"

// Firmware version - CHANGE THIS FOR EACH UPDATE
#define FIRMWARE_VERSION "1.0.0"

// WiFi credentials
const char* ssid = "iMES";
const char* password = "Imes@2025";

// ThingsBoard MQTT broker
const char* mqtt_server = "192.168.1.95";
const int mqtt_port = 8883;

// MQTT topics
const char* telemetry_topic = "v1/devices/me/telemetry";
const char* attributes_topic = "v1/devices/me/attributes";

// Global objects
WiFiClientSecure espClient;
PubSubClient client(espClient);

// OTA update variables
String fw_version_available = "";
String fw_url = "";
String fw_checksum = "";

// Get MAC address as device name
String getDeviceName() {
  uint8_t mac[6];
  WiFi.macAddress(mac);
  char macStr[13];
  sprintf(macStr, "%02X%02X%02X%02X%02X%02X", mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
  return String(macStr);
}

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("🌐 Connecting to WiFi: ");
  Serial.println(ssid);

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.println("✅ WiFi connected");
  Serial.print("📍 IP address: ");
  Serial.println(WiFi.localIP());
  Serial.print("📱 MAC address: ");
  Serial.println(getDeviceName());
}

void setup_certificates() {
  Serial.println("🔐 Loading certificates...");
  
  espClient.setCACert(ca_cert);
  espClient.setCertificate(device_cert);
  espClient.setPrivateKey(device_key);
  
  Serial.println("✅ Certificates loaded");
}

void performOTAUpdate() {
  if (fw_url.length() == 0) {
    Serial.println("❌ No firmware URL provided");
    return;
  }

  Serial.println("\n========================================");
  Serial.println("📥 OTA Update Starting");
  Serial.println("========================================");
  Serial.print("Version: ");
  Serial.println(fw_version_available);
  Serial.print("URL: ");
  Serial.println(fw_url);
  
  
  WiFiClient otaClient;
  
  httpUpdate.rebootOnUpdate(false);
  
  t_httpUpdate_return ret = httpUpdate.update(otaClient, fw_url);
  
  switch (ret) {
    case HTTP_UPDATE_FAILED:
      Serial.println("❌ OTA Update failed");
      Serial.printf("Error (%d): %s\n", httpUpdate.getLastError(), httpUpdate.getLastErrorString().c_str());
      break;
      
    case HTTP_UPDATE_NO_UPDATES:
      Serial.println("ℹ️  No updates available");
      break;
      
    case HTTP_UPDATE_OK:
      Serial.println("✅ OTA Update successful!");
      Serial.println("🔄 Rebooting...");
      delay(1000);
      ESP.restart();
      break;
  }
  
  Serial.println("========================================\n");
}

void callback(char* topic, byte* payload, unsigned int length) {
  Serial.print("📨 Message [");
  Serial.print(topic);
  Serial.print("]: ");
  
  char message[length + 1];
  for (int i = 0; i < length; i++) {
    message[i] = (char)payload[i];
  }
  message[length] = '\0';
  Serial.println(message);
  
  // Check if this is a shared attributes update (OTA trigger)
  if (String(topic).indexOf("attributes") >= 0) {
    StaticJsonDocument<512> doc;
    DeserializationError error = deserializeJson(doc, message);
    
    if (!error) {
      // Check for firmware update attributes
      if (doc.containsKey("fw_version")) {
        fw_version_available = doc["fw_version"].as<String>();
        
        if (fw_version_available != FIRMWARE_VERSION) {
          Serial.println("\n🆕 New firmware version available!");
          Serial.print("   Current: ");
          Serial.println(FIRMWARE_VERSION);
          Serial.print("   Available: ");
          Serial.println(fw_version_available);
          
          if (doc.containsKey("fw_url")) {
            fw_url = doc["fw_url"].as<String>();
          }
          
          if (doc.containsKey("fw_checksum")) {
            fw_checksum = doc["fw_checksum"].as<String>();
          }
          
          // Trigger OTA update
          performOTAUpdate();
        } else {
          Serial.println("ℹ️  Firmware is up to date");
        }
      }
    }
  }
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("🔌 Attempting MQTT connection...");
    
    String deviceName = getDeviceName();
    
    if (client.connect(deviceName.c_str())) {
      Serial.println("✅ Connected to ThingsBoard!");
      Serial.print("📱 Device name: ");
      Serial.println(deviceName);
      
      // Subscribe to shared attributes (for OTA updates)
      client.subscribe("v1/devices/me/attributes");
      client.subscribe("v1/devices/me/attributes/response/+");
      client.subscribe("v1/devices/me/rpc/request/+");
      
      // Report current firmware version
      String versionPayload = "{\"fw_version\":\"" + String(FIRMWARE_VERSION) + "\"}";
      client.publish(attributes_topic, versionPayload.c_str());
      Serial.print("📤 Reported firmware version: ");
      Serial.println(FIRMWARE_VERSION);
      
    } else {
      Serial.print("❌ Failed, rc=");
      Serial.print(client.state());
      Serial.println(" - Retrying in 5 seconds...");
      
      if (client.state() == -2) {
        Serial.println("   Error: MQTT_CONNECT_FAILED (Network issue)");
      } else if (client.state() == 5) {
        Serial.println("   Error: MQTT_CONNECT_UNAUTHORIZED (Check certificates!)");
      }
      
      delay(5000);
    }
  }
}

void sendTelemetry() {
  StaticJsonDocument<256> doc;
  doc["temperature"] = random(20, 30);
  doc["humidity"] = random(40, 60);
  doc["uptime"] = millis() / 1000;
  doc["fw_version"] = FIRMWARE_VERSION;
  
  String payload;
  serializeJson(doc, payload);
  
  Serial.print("📤 Sending telemetry: ");
  Serial.println(payload);
  
  if (client.publish(telemetry_topic, payload.c_str())) {
    Serial.println("✅ Telemetry sent successfully");
  } else {
    Serial.println("❌ Failed to send telemetry");
  }
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n\n");
  Serial.println("========================================");
  Serial.println("🚀 ESP32 X.509 + OTA");
  Serial.print("📦 Firmware version: ");
  Serial.println(FIRMWARE_VERSION);
  Serial.println("========================================");
  
  setup_wifi();
  setup_certificates();
  
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
  client.setKeepAlive(60);
  client.setBufferSize(512);
  
  Serial.println("========================================");
  Serial.println("✨ Setup complete!");
  Serial.println("========================================\n");
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();
  
  static unsigned long lastMsg = 0;
  unsigned long now = millis();
  
  if (now - lastMsg > 10000) {
    lastMsg = now;
    sendTelemetry();
  }
}
