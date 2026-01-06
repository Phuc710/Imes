# 🚀 Hướng Dẫn Setup OTA trên ThingsBoard

## Bước 1: Upload Firmware lên ThingsBoard

✅ **BẠN ĐÃ LÀM XONG BƯỚC NÀY!**

Firmware đã upload:
- Title: `TEST`
- Version: `1.0`
- Device profile: `okee`
- File: `ESP32_X509.ino.bin`

---

## Bước 2: Trigger OTA Update từ ThingsBoard UI

### Cách 1: Qua Device Attributes (DỄ NHẤT)

1. **Vào Devices** → Click device `A842E3578AD4`

2. **Tab "Attributes"** → **"Shared attributes"**

3. Click **"+"** (Add attribute)

4. **Thêm attribute:**
   - Key: `fw_version`
   - Value type: `String`
   - Value: `1.0`

5. Click **"Add"**

ESP32 sẽ nhận được ngay và bắt đầu download!

### Cách 2: Qua OTA Updates Tab

1. Vào device `A842E3578AD4`

2. Tab **"OTA updates"**

3. Click **"Assign firmware"**

4. Chọn package **"TEST"** version **"1.0"**

5. Click **"Assign"**

---

## Bước 3: Monitor ESP32

Mở **Serial Monitor** (115200 baud), bạn sẽ thấy:

```
📨 Message [v1/devices/me/attributes]: {"fw_version":"1.0"}
🆕 New firmware version available!
   Current: 1.0.0
   Available: 1.0
📥 OTA Update Starting
========================================
Version: 1.0
URL: http://thingsboard-url/firmware/...
✅ OTA Update successful!
🔄 Rebooting...
```

---

## ⚠️ LƯU Ý QUAN TRỌNG

### 1. Firmware Version Phải Khác Nhau

Trong code ESP32:
```cpp
#define FIRMWARE_VERSION "1.0.0"
```

Trong ThingsBoard:
```
fw_version: "1.0"
```

**Chúng PHẢI KHÁC NHAU** thì ESP32 mới download!

### 2. ThingsBoard Cần Có Firmware URL

ThingsBoard sẽ tự động tạo URL khi bạn upload firmware. ESP32 sẽ nhận URL này qua shared attributes.

### 3. Libraries Cần Thiết

Trong Arduino IDE, cài đặt:
- **HTTPUpdate** (built-in với ESP32)
- **ArduinoJson** (Library Manager → Search "ArduinoJson")

---

## 🔧 Troubleshooting

### ESP32 không nhận update

**Kiểm tra:**
1. ESP32 đã connected to ThingsBoard chưa?
2. Serial Monitor có thấy message `📨 Message [v1/devices/me/attributes]` không?
3. Firmware version trong code khác với version trong ThingsBoard chưa?

### Lỗi "Failed to download"

**Nguyên nhân:** ESP32 không kết nối được đến ThingsBoard firmware URL

**Giải pháp:**
- Kiểm tra WiFi connection
- Kiểm tra ThingsBoard có public access không
- Thử dùng HTTP server riêng (firmware_server.py)

### Lỗi "Update failed"

**Nguyên nhân:** Firmware corrupt hoặc không đúng format

**Giải pháp:**
- Build lại firmware trong Arduino IDE
- Đảm bảo file .bin không bị corrupt
- Kiểm tra partition scheme đủ lớn

---

## 📊 Flow Hoàn Chỉnh

```
1. Build firmware trong Arduino IDE
         ↓
2. Upload .bin lên ThingsBoard (✅ ĐÃ LÀM)
         ↓
3. Set shared attribute fw_version = "1.0"
         ↓
4. ESP32 nhận notification
         ↓
5. ESP32 download firmware từ ThingsBoard
         ↓
6. ESP32 install & reboot
         ↓
7. ESP32 report version mới
```

---

## 🎯 Test Ngay

**Làm theo:**
1. Upload code `ESP32_X509.ino` lên ESP32
2. Mở Serial Monitor
3. Vào ThingsBoard → Device → Attributes → Add `fw_version: "1.0"`
4. Xem ESP32 tự động update!

**Nếu thành công**, bạn sẽ thấy ESP32 reboot và report version mới! 🎉
