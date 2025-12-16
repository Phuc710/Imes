#include "esp_camera.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// ================== WIFI ==================
const char* ssid = "iMES";
const char* password = "Imes@2025";

// ================== SERVER ==================
const char* serverUrl = "http://103.249.117.210:3340/ocr/kafka?camera_id=2&save_img=false";
const char* thingboardUrl = "http://192.168.1.71:8080/api/v1/Tr8PSFI7PC796rBcSjRW/telemetry";

// ================== CAMERA PIN (AI THINKER) ==================
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27

#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

// ================== SETUP ==================
void setup() {
  Serial.begin(115200);
  delay(1000);

  // -------- Camera config --------
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer   = LEDC_TIMER_0;
  config.pin_d0       = Y2_GPIO_NUM;
  config.pin_d1       = Y3_GPIO_NUM;
  config.pin_d2       = Y4_GPIO_NUM;
  config.pin_d3       = Y5_GPIO_NUM;
  config.pin_d4       = Y6_GPIO_NUM;
  config.pin_d5       = Y7_GPIO_NUM;
  config.pin_d6       = Y8_GPIO_NUM;
  config.pin_d7       = Y9_GPIO_NUM;
  config.pin_xclk     = XCLK_GPIO_NUM;
  config.pin_pclk     = PCLK_GPIO_NUM;
  config.pin_vsync    = VSYNC_GPIO_NUM;
  config.pin_href     = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn     = PWDN_GPIO_NUM;
  config.pin_reset    = RESET_GPIO_NUM;

  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;

  // Giảm độ phân giải để tiết kiệm memory
  config.frame_size   = FRAMESIZE_SVGA;   // 800x600
  config.jpeg_quality = 12;               // Giảm chất lượng để nhỏ hơn
  config.fb_count     = 1;                // Chỉ 1 framebuffer

  // -------- Init camera --------
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("❌ Camera init failed: 0x%x\n", err);
    while(1) { delay(1000); }
  }

  // Cấu hình sensor
  sensor_t * s = esp_camera_sensor_get();
  if (s) {
    s->set_brightness(s, 0);
    s->set_contrast(s, 0);
    s->set_saturation(s, 0);
    s->set_sharpness(s, 0);
    s->set_whitebal(s, 1);
    s->set_awb_gain(s, 1);
    s->set_wb_mode(s, 0);
    s->set_exposure_ctrl(s, 1);
    s->set_aec2(s, 0);
    s->set_ae_level(s, 0);
    s->set_aec_value(s, 300);
    s->set_gain_ctrl(s, 1);
    s->set_agc_gain(s, 0);
    s->set_gainceiling(s, (gainceiling_t)0);
    s->set_bpc(s, 0);
    s->set_wpc(s, 1);
    s->set_raw_gma(s, 1);
    s->set_lenc(s, 1);
    s->set_hmirror(s, 0);
    s->set_vflip(s, 0);
    s->set_dcw(s, 1);
    s->set_colorbar(s, 0);
  }

  // -------- Connect WiFi --------
  WiFi.begin(ssid, password);
  Serial.print("Connecting WiFi");
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✅ WiFi connected");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n❌ WiFi connection failed!");
    while(1) { delay(1000); }
  }
}

// ================== LOOP ==================
void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("⚠️ WiFi disconnected! Reconnecting...");
    WiFi.reconnect();
    delay(5000);
    return;
  }

  sendPhoto();
  delay(3000);  // Tăng delay để ổn định
}

// ================== SEND TO THINGSBOARD ==================
void sendToThingsBoard(String ocrStatus, String ocrText, unsigned long processingTime) {
  WiFiClient client;
  HTTPClient http;
  
  if (!http.begin(client, thingboardUrl)) {
    Serial.println("❌ Thingsboard begin failed");
    return;
  }
  
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(10000);
  
  // JSON nhỏ gọn
  StaticJsonDocument<256> doc;
  doc["status"] = ocrStatus;
  doc["text"] = ocrText;
  doc["time_ms"] = processingTime;
  
  String payload;
  serializeJson(doc, payload);
  
  Serial.println("📦Thingsboard: " + payload);
  
  int code = http.POST(payload);
  Serial.printf("📦status: %d (%lu ms)\n", code, processingTime);
  
  http.end();
  client.stop();
  delay(50);
}

// ================== SEND PHOTO ==================
void sendPhoto() {
  Serial.println("\n=== ESp32 CAM TEST  ===");

  // Capture
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("❌ Capture failed");
    sendToThingsBoard("error", "Capture failed", 0);
    return;
  }

  Serial.printf("📷 Size: %d bytes (%.1f KB)\n", fb->len, fb->len / 1024.0);

  // Tạo multipart body - PHƯƠNG PHÁP ĐƠN GIẢN NHẤT
  String boundary = "----TEST";
  
  String head = "--" + boundary + "\r\n";
  head += "Content-Disposition: form-data; name=\"file\"; filename=\"esp32cam.jpg\"\r\n";
  head += "Content-Type: image/jpeg\r\n\r\n";
  
  String tail = "\r\n--" + boundary + "--\r\n";

  // Tính tổng size
  uint32_t totalLen = head.length() + fb->len + tail.length();

  // Allocate buffer nhỏ hơn nếu có thể
  uint8_t *fullBody = (uint8_t*)ps_malloc(totalLen);  // Dùng PSRAM nếu có
  if (!fullBody) {
    fullBody = (uint8_t*)malloc(totalLen);  // Fallback to heap
    if (!fullBody) {
      Serial.println("❌ Memory allocation failed!");
      esp_camera_fb_return(fb);
      sendToThingsBoard("error", "Out of memory", 0);
      return;
    }
  }

  // Copy data
  memcpy(fullBody, head.c_str(), head.length());
  memcpy(fullBody + head.length(), fb->buf, fb->len);
  memcpy(fullBody + head.length() + fb->len, tail.c_str(), tail.length());

  // HTTP Request
  WiFiClient client;
  HTTPClient http;

  unsigned long startTime = millis();
  
  if (!http.begin(client, serverUrl)) {
    Serial.println("❌ HTTP begin failed");
    free(fullBody);
    esp_camera_fb_return(fb);
    sendToThingsBoard("error", "HTTP begin failed", 0);
    return;
  }

  http.addHeader("Content-Type", "multipart/form-data; boundary=" + boundary);
  http.setTimeout(20000);

  Serial.println("Sending POST...");
  int httpCode = http.POST(fullBody, totalLen);
  
  unsigned long processingTime = millis() - startTime;
  Serial.printf("📥 OCR Status: %d (%lu ms)\n", httpCode, processingTime);

  // Parse response
  if (httpCode == 200) {
    String response = http.getString();
    Serial.println("✅ Response OCR: " + response.substring(0, 200));  // Chỉ log 200 ký tự
    
    DynamicJsonDocument doc(1024);
    DeserializationError error = deserializeJson(doc, response);
    
    if (!error) {
      bool success = doc["success"] | false;
      int count = doc["count"] | 0;
      
      String ocrText = "No text";
      if (count > 0 && doc["ocr_results"].size() > 0) {
        JsonVariant textValue = doc["ocr_results"][0]["text"];
        if (textValue.is<int>()) {
          ocrText = String(textValue.as<int>());
        } else if (textValue.is<const char*>()) {
          ocrText = textValue.as<String>();
        }
      }
      
      sendToThingsBoard(success ? "success" : "failed", ocrText, processingTime);
      
    } else {
      Serial.println("⚠️ JSON parse error");
      sendToThingsBoard("error", "Parse failed", processingTime);
    }
    
  } else if (httpCode > 0) {
    Serial.printf("⚠️ HTTP error: %d\n", httpCode);
    sendToThingsBoard("error", "HTTP " + String(httpCode), processingTime);
  } else {
    Serial.printf("❌ Connection failed: %s\n", http.errorToString(httpCode).c_str());
    sendToThingsBoard("error", "Connection failed", processingTime);
  }

  // Cleanup - QUAN TRỌNG
  http.end();
  client.stop();
  free(fullBody);
  esp_camera_fb_return(fb);
  
  delay(100);  // Đợi cleanup hoàn toàn
  
}