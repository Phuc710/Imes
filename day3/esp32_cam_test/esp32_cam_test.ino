#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
// ===== CẤU HÌNH WIFI =====
const char* ssid = "iMES";        // Thay bằng tên WiFi của bạn
const char* password = "Imes@2025"; // Thay bằng mật khẩu WiFi
// ===== CẤU HÌNH MQTT GATEWAY =====
const char* mqtt_server = "192.168.1.72";    // Thay bằng IP máy tính chạy Docker
const int mqtt_port = 18883;                 // Port Gateway MQTT
const char* device_name = "ESP32_Sensor_01"; // Tên device (unique cho mỗi ESP32)
// ===== MQTT TOPIC =====
// Format: sensor/<device_name>/telemetry
String telemetry_topic = "sensor/" + String(device_name) + "/telemetry";
WiFiClient espClient;
PubSubClient client(espClient);
// ===== BIẾN GIẢ LẬP CẢM BIẾN =====
// Thay bằng code đọc cảm biến thật (DHT22, BME280, etc.)
float temperature = 25.0;
float humidity = 60.0;
// ===== HÀM KẾT NỐI WIFI =====
void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.println("WiFi connected!");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
}
// ===== HÀM KẾT NỐI LẠI MQTT =====
void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    
    // Kết nối với Client ID
    if (client.connect(device_name)) {
      Serial.println("connected!");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}
// ===== HÀM GỬI DỮ LIỆU TELEMETRY =====
void sendTelemetry() {
  // Tạo JSON payload
  StaticJsonDocument<200> doc;
  doc["temperature"] = temperature;
  doc["humidity"] = humidity;
  
  // Serialize JSON thành string
  String payload;
  serializeJson(doc, payload);
  
  // Publish lên MQTT
  if (client.publish(telemetry_topic.c_str(), payload.c_str())) {
    Serial.println("✅ Telemetry sent: " + payload);
  } else {
    Serial.println("❌ Failed to send telemetry");
  }
}
// ===== SETUP =====
void setup() {
  Serial.begin(115200);
  
  // Kết nối WiFi
  setup_wifi();
  
  // Cấu hình MQTT server
  client.setServer(mqtt_server, mqtt_port);
  
  Serial.println("=================================");
  Serial.println("ESP32 Gateway Client Started");
  Serial.println("Device: " + String(device_name));
  Serial.println("Topic: " + telemetry_topic);
  Serial.println("=================================");
}
// ===== LOOP =====
void loop() {
  // Đảm bảo MQTT luôn kết nối
  if (!client.connected()) {
    reconnect();
  }
  client.loop();
  
  // ===== ĐỌC CẢM BIẾN =====
  // Giả lập dữ liệu cảm biến (thay đổi ngẫu nhiên)
  // TODO: Thay bằng code đọc cảm biến thật
temperature = 20.0 + random(0, 100) / 10.0;  // 20.0 - 30.0°C
humidity = 50.0 + random(0, 300) / 10.0;     // 50.0 - 80.0%
  
  // Gửi dữ liệu mỗi 5 giây
  sendTelemetry();
  delay(5000);
}