#include "esp_camera.h"
#include <WiFi.h>
#include <HTTPClient.h>

// ================= WIFI =================
#define WIFI_SSID     "iMES"
#define WIFI_PASSWORD "Imes@2025"

// ================= THINGSBOARD =================
#define TB_HOST  "192.168.1.71"      // IP ThingsBoard
#define TB_PORT  8080
#define TB_TOKEN "ZA88bSL1qLkzuzEI2t0G"

// ================= CAMERA PIN (AI THINKER) =================
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

// ================= GLOBAL =================
String tbUrl;
unsigned long lastTelemetry = 0;
unsigned long lastCapture = 0;

// ================= WIFI =================
void connectWiFi() {
  Serial.print("Connecting WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());
}

// ================= CAMERA =================
bool initCamera() {
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

  // ===== MAX RESOLUTION =====
  config.frame_size   = FRAMESIZE_UXGA;   // 1600x1200
  config.jpeg_quality = 15;
  config.fb_count     = 2;

  if (esp_camera_init(&config) != ESP_OK) {
    Serial.println("Camera init FAILED");
    return false;
  }

  Serial.println("Camera init OK");
  return true;
}

// ================= SEND TO OCR API =================
void sendToOCR() {
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Capture FAILED");
    return;
  }

  Serial.print("Captured image size: ");
  Serial.print(fb->len);
  Serial.println(" bytes");

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi not connected");
    esp_camera_fb_return(fb);
    return;
  }

  WiFiClient client;
  const char* host = "127.0.0.1";
  int port = 8000;
  String path = "/v1/ocr";

  // Kết nối tới server với timeout
  client.setTimeout(10000);
  if (!client.connect(host, port)) {
    esp_camera_fb_return(fb);
    return;
  }

  Serial.println("[OCR] Connected to server");

  // Xây dựng multipart form data
  String boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW";
  String startBoundary = "--" + boundary + "\r\n";
  String contentDisposition = "Content-Disposition: form-data; name=\"file\"; filename=\"esp32_cam.jpg\"\r\n";
  String contentType = "Content-Type: image/jpeg\r\n\r\n";
  String endBoundary = "\r\n--" + boundary + "--\r\n";

  // Tính toán Content-Length
  uint32_t contentLength = startBoundary.length() + contentDisposition.length() + 
                          contentType.length() + fb->len + endBoundary.length();

  // Gửi HTTP request header
  client.print("POST ");
  client.print(path);
  client.println(" HTTP/1.1");
  client.print("Host: ");
  client.print(host);
  client.print(":");
  client.println(port);
  client.println("Connection: close");
  client.print("Content-Type: multipart/form-data; boundary=");
  client.println(boundary);
  client.print("Content-Length: ");
  client.println(contentLength);
  client.println();

  // Gửi multipart body
  client.print(startBoundary);
  client.print(contentDisposition);
  client.print(contentType);
  
  client.write(fb->buf, fb->len);
  client.print(endBoundary);

  // Đợi response
  delay(1000);

  // Đọc response
  String response = "";
  while (client.connected() || client.available()) {
    if (client.available()) {
      String line = client.readStringUntil('\n');
      response += line;
    }
  }

  client.stop();

  // Trích xuất JSON từ response (bỏ qua HTTP header)
  int jsonStart = response.indexOf('{');
  if (jsonStart >= 0) {
    String jsonResponse = response.substring(jsonStart);
    sendOCRResultToThingsBoard(jsonResponse);
  }  esp_camera_fb_return(fb);
}

// ================= SEND OCR RESULT TO THINGSBOARD =================
void sendOCRResultToThingsBoard(String ocrResponse) {
  if (WiFi.status() != WL_CONNECTED) return;

  HTTPClient http;
  WiFiClient client;

  http.begin(client, tbUrl);
  http.addHeader("Content-Type", "application/json");

  unsigned long currentTime = millis();

  // Xây dựng payload với OCR text và thời gian nhận diện
  String payload = "{";
  payload += "\"ocr_text\":\"" + ocrResponse + "\",";
  payload += "\"ocr_time\":" + String(currentTime) + ",";
  payload += "\"status\":\"online\"";
  payload += "}";

  http.POST(payload);
  http.end();
}

// ================= SEND TELEMETRY =================
void sendTelemetry() {
  if (WiFi.status() != WL_CONNECTED) return;

  HTTPClient http;
  WiFiClient client;

  http.begin(client, tbUrl);
  http.addHeader("Content-Type", "application/json");

  unsigned long uptime = millis() / 1000;

  String payload = "{";
  payload += "\"status\":\"online\",";
  payload += "\"uptime\":" + String(uptime) + ",";
  payload += "\"rssi\":" + String(WiFi.RSSI());
  payload += "}";

  http.POST(payload);
  http.end();
}


// ================= SETUP =================
void setup() {
  Serial.begin(115200);
  delay(1000);

  if (!initCamera()) {
    while (true) delay(1000);
  }

  connectWiFi();

  tbUrl = "http://" + String(TB_HOST) + ":" + String(TB_PORT) +
          "/api/v1/" + String(TB_TOKEN) + "/telemetry";

  Serial.println("ESP32 READY");
}

// ================= LOOP =================
void loop() {
  // gửi telemetry mỗi 5 giây
  if (millis() - lastTelemetry > 5000) {
    lastTelemetry = millis();
    sendTelemetry();
  }

  // chụp ảnh và gửi lên OCR mỗi 10 giây
  if (millis() - lastCapture > 10000) {
    lastCapture = millis();
    sendToOCR();
  }

  delay(100);
}
