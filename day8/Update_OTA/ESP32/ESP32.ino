#include <WiFi.h>
#include <WiFiManager.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <Preferences.h>

// OTA
#include <HTTPClient.h>
#include <Update.h>
#include <mbedtls/sha256.h>

// ===== FW VERSION (tự tăng khi build bản mới) =====
#define FW_VER  "1"

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

// ===== VERSION =====
static int verToInt(const String& v) {
  // rất đơn giản: "2"->2, "10"->10
  return v.toInt();
}

// ===== SHA256 HELPERS =====
static String sha256ToHex(const uint8_t* hash, size_t len = 32) {
  const char hex[] = "0123456789abcdef";
  String out;
  out.reserve(len * 2);
  for (size_t i = 0; i < len; i++) {
    out += hex[(hash[i] >> 4) & 0xF];
    out += hex[hash[i] & 0xF];
  }
  return out;
}

// ===== OTA (chunked + sha256 verify) =====
static bool otaHttpUpdateSha256(const String& url, const String& expectedSha256) {
  Serial.println("OTA: start with SHA256 verify");
  Serial.println("OTA: url=" + url);

  HTTPClient http;
  http.setFollowRedirects(HTTPC_STRICT_FOLLOW_REDIRECTS);

  if (!http.begin(url)) {
    Serial.println("OTA: http begin fail");
    return false;
  }

  int code = http.GET();
  if (code != HTTP_CODE_OK) {
    Serial.printf("OTA: http code=%d\n", code);
    http.end();
    return false;
  }

  WiFiClient* stream = http.getStreamPtr();

  // ✅ Cho phép chunked: không cần Content-Length
  if (!Update.begin(UPDATE_SIZE_UNKNOWN)) {
    Serial.println("OTA: Update.begin fail");
    http.end();
    return false;
  }

  // SHA256 init
  mbedtls_sha256_context ctx;
  mbedtls_sha256_init(&ctx);
  mbedtls_sha256_starts(&ctx, 0);  // 0 = SHA256

  uint8_t buf[1024];
  int total = 0;
  unsigned long lastData = millis();

  while (http.connected()) {
    size_t available = stream->available();
    if (available) {
      int readLen = stream->readBytes(buf, (available > sizeof(buf)) ? sizeof(buf) : available);
      if (readLen <= 0) break;

      // update sha256
      mbedtls_sha256_update(&ctx, buf, readLen);

      // write to flash
      size_t written = Update.write(buf, readLen);
      if (written != (size_t)readLen) {
        Serial.printf("OTA: write fail %u/%d\n", (unsigned)written, readLen);
        Update.abort();
        http.end();
        return false;
      }

      total += readLen;
      lastData = millis();
    } else {
      // timeout protection
      if (millis() - lastData > 15000) {
        Serial.println("OTA: timeout waiting data");
        Update.abort();
        http.end();
        return false;
      }
      delay(1);
    }
  }

  // finalize sha256
  uint8_t hash[32];
  mbedtls_sha256_finish(&ctx, hash);
  mbedtls_sha256_free(&ctx);

  String gotSha = sha256ToHex(hash);

  Serial.println("OTA: downloaded bytes=" + String(total));
  Serial.println("OTA: expected sha256=" + expectedSha256);
  Serial.println("OTA: got      sha256=" + gotSha);

  // check hash
  if (expectedSha256.length() > 0 && gotSha != expectedSha256) {
    Serial.println("OTA: SHA256 mismatch -> abort");
    Update.abort();
    http.end();
    return false;
  }

  if (!Update.end(true)) {
    Serial.printf("OTA: end fail err=%d\n", Update.getError());
    http.end();
    return false;
  }

  if (!Update.isFinished()) {
    Serial.println("OTA: not finished");
    http.end();
    return false;
  }

  http.end();
  Serial.println("OTA: OK -> reboot");
  delay(300);
  ESP.restart();
  return true;
}

// ===== MQTT CALLBACK =====
void onMqtt(char* topic, byte* payload, unsigned int length) {
  String t = String(topic);

  String msg;
  msg.reserve(length + 1);
  for (unsigned int i = 0; i < length; i++) msg += (char)payload[i];

  // 1) Provision response
  if (t == "/provision/response") {
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
    return;
  }

  // 2) RPC (OTA)
  if (t.startsWith("v1/devices/me/rpc/request/")) {
    DynamicJsonDocument doc(1024);
    if (deserializeJson(doc, msg)) {
      Serial.println("RPC: JSON loi");
      return;
    }

    const char* method = doc["method"] | "";
    if (String(method) != "ota") return;

    String url    = doc["params"]["url"] | "";
    String newVer = doc["params"]["ver"] | "";
    String sha256 = doc["params"]["sha256"] | "";

    Serial.println("RPC: ota");

    if (url.length() == 0) {
      Serial.println("OTA: thieu url");
      return;
    }

    int cur = verToInt(String(FW_VER));
    int nxt = verToInt(newVer);

    if (newVer.length() > 0 && nxt <= cur) {
      Serial.printf("OTA: bo qua (cur=%d, nxt=%d)\n", cur, nxt);
      return;
    }

    // chỉ cho OTA khi đang là device (đã có token)
    if (!provisioned || !mqttConnected) {
      Serial.println("OTA: chua device online");
      return;
    }

    // ✅ OTA + SHA256 verify + chunked
    otaHttpUpdateSha256(url, sha256);
    return;
  }
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
  if (!wm.autoConnect("ESP32_Provision_AP", "12345678")) {
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

      // bật RPC để nhận OTA
      mqtt.subscribe("v1/devices/me/rpc/request/+");
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

  Serial.print("FW: ");
  Serial.println(FW_VER);

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
    d["fw"]          = FW_VER; // tiện xem version trên TB

    char buf[160];
    size_t n = serializeJson(d, buf, sizeof(buf));

    Serial.print("PUB: ");
    Serial.write((uint8_t*)buf, n);
    Serial.println();

    mqtt.publish("v1/devices/me/telemetry", (uint8_t*)buf, n);
  }
}
