#include <WiFi.h>
#include <WiFiManager.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <Preferences.h>

// ===== THINGSBOARD =====
const char* TB_HOST = "192.168.1.95";
const int   TB_PORT = 1883;

#define PROVISION_KEY    "aqtz9husob3m1gxcexyj"
#define PROVISION_SECRET "f24l3p2xfqdjmq95m1os"

// ===== ESP32 DEVKIT =====
static const int BTN_BOOT_PIN = 0;        // BOOT = GPIO0
static const uint32_t HOLD_MS = 3000;     // giữ 3s để xoá all

// ===== GLOBAL =====
WiFiClient espClient;
PubSubClient mqtt(espClient);
Preferences prefs;                        // namespace "tb"

String deviceName;
String accessToken;
bool provisioned = false;
bool mqttConnected = false;

uint32_t lastReconnectAttempt = 0;
uint32_t lastSend = 0;

// ===== HELPERS =====
static String macToName() {
  uint8_t mac[6];
  WiFi.macAddress(mac);
  char s[13];
  snprintf(s, sizeof(s), "%02X%02X%02X%02X%02X%02X",
           mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
  return "ESP32-" + String(s);
}

static void factoryResetAll() {
  Serial.println("FR: xoa WiFi+token");
  WiFi.disconnect(true, true);     // xoá Wi-Fi đã lưu
  delay(200);

  prefs.begin("tb", false);
  prefs.clear();                   // xoá access_token + device_name
  prefs.end();

  Serial.println("FR: reboot");
  delay(300);
  ESP.restart();
}

// ===== MQTT CALLBACK =====
void onMqtt(char* topic, byte* payload, unsigned int length) {
  if (String(topic) != "/provision/response") return;

  String msg;
  msg.reserve(length + 1);
  for (unsigned int i = 0; i < length; i++) msg += (char)payload[i];

  DynamicJsonDocument doc(512);
  if (deserializeJson(doc, msg)) {
    Serial.println("PRV: JSON loi");
    return;
  }

  String st = doc["status"] | doc["provisionDeviceStatus"] | "";
  if (st != "SUCCESS") {
    String em = doc["errorMsg"] | "FAIL";
    Serial.println("PRV: loi");
    Serial.println(em);
    return;
  }

  String token = doc["credentialsValue"] | doc["accessToken"] | "";
  if (token.length() == 0) {
    Serial.println("PRV: thieu token");
    return;
  }

  accessToken = token;
  provisioned = true;

  prefs.begin("tb", false);
  prefs.putString("access_token", accessToken);
  prefs.putString("device_name", deviceName);
  prefs.end();

  Serial.println("PRV: OK");
  mqttConnected = false;
  mqtt.disconnect(); // reconnect sang mode device
}

// ===== STATE/WIFI =====
static void loadState() {
  prefs.begin("tb", true);
  accessToken = prefs.getString("access_token", "");
  deviceName  = prefs.getString("device_name", "");
  prefs.end();

  provisioned = (accessToken.length() > 0);
}

static void connectWiFi() {
  WiFiManager wm;
  wm.setConfigPortalTimeout(180);

  Serial.println("WiFi: connect");
  if (!wm.autoConnect("imes", "12345678")) {
    Serial.println("WiFi: fail");
    delay(300);
    ESP.restart();
  }
  Serial.print("WiFi: OK ");
  Serial.println(WiFi.localIP());
}

// ===== MQTT CONNECT =====
static void mqttReconnect() {
  mqttConnected = false;
  String cid = "ESP32-" + String((uint32_t)ESP.getEfuseMac(), HEX);

  if (provisioned) {
    if (mqtt.connect(cid.c_str(), accessToken.c_str(), "")) {
      mqttConnected = true;
      Serial.println("MQTT: device OK");
    } else {
      Serial.print("MQTT: fail ");
      Serial.println(mqtt.state());
    }
    return;
  }

  if (mqtt.connect(cid.c_str(), "provision", "")) {
    Serial.println("MQTT: prov OK");
    mqtt.subscribe("/provision/response");

    DynamicJsonDocument d(256);
    d["deviceName"] = deviceName;
    d["provisionDeviceKey"] = PROVISION_KEY;
    d["provisionDeviceSecret"] = PROVISION_SECRET;

    char buf[256];
    size_t n = serializeJson(d, buf, sizeof(buf));
    mqtt.publish("/provision/request", (uint8_t*)buf, n);
    Serial.println("PRV: send");
  } else {
    Serial.print("MQTT: fail ");
    Serial.println(mqtt.state());
  }
}

// ===== SETUP/LOOP =====
void setup() {
  Serial.begin(115200);
  delay(200);

  pinMode(BTN_BOOT_PIN, INPUT_PULLUP);

  loadState();
  connectWiFi();

  if (deviceName.length() == 0) deviceName = macToName();
  Serial.print("DEV: ");
  Serial.println(deviceName);

  Serial.println(provisioned ? "PRV: co token" : "PRV: can provision");

  mqtt.setServer(TB_HOST, TB_PORT);
  mqtt.setCallback(onMqtt);
}

void loop() {
  // Giữ BOOT 3s bất kỳ lúc nào -> xoá all
  static uint32_t btnHoldMs = 0;
  if (digitalRead(BTN_BOOT_PIN) == LOW) {
    if (btnHoldMs == 0) btnHoldMs = millis();
    if (millis() - btnHoldMs > HOLD_MS) factoryResetAll();
  } else {
    btnHoldMs = 0;
  }

  // MQTT maintain
  if (!mqtt.connected()) {
    uint32_t now = millis();
    if (now - lastReconnectAttempt > 3000) {
      lastReconnectAttempt = now;
      mqttReconnect();
    }
  }
  mqtt.loop();

  // Telemetry mỗi 10s khi đã provision
  if (provisioned && mqttConnected && millis() - lastSend > 10000) {
    lastSend = millis();

    DynamicJsonDocument d(128);
    d["temperature"] = random(20, 35);
    d["humidity"]    = random(40, 80);

    char buf[128];
    size_t n = serializeJson(d, buf, sizeof(buf));
    Serial.print("PUB -> v1/devices/me/telemetry: ");
    Serial.write((uint8_t*)buf, n);
    Serial.println();
    mqtt.publish("v1/devices/me/telemetry", (uint8_t*)buf, n);
  }
}
