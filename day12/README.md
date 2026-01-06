# 🔐 ESP32 X.509 Auto-Provisioning với ThingsBoard

Hệ thống auto-provisioning hoàn chỉnh sử dụng X.509 certificates cho ESP32 kết nối với ThingsBoard qua MQTT SSL/TLS.

## 📋 Danh Sách File

### 1️⃣ Docker / ThingsBoard
- ✅ `docker-compose.yml` - Chạy ThingsBoard với MQTT SSL
- ✅ ThingsBoard đã được cấu hình sẵn X.509 auto-provisioning

### 2️⃣ PKI / Certificates
- ✅ `gen_certs.py` - Script Python sinh certificates
- 📁 `certs/` - Thư mục chứa certificates (tự động tạo)
  - `root_ca.pem` - CA certificate (paste vào ThingsBoard)
  - `root_ca.key` - CA private key (**KHÔNG BAO GIỜ** upload lên ThingsBoard)
  - `{MAC_ADDRESS}.crt` - Device certificate
  - `{MAC_ADDRESS}.key` - Device private key

### 3️⃣ ESP32
- ✅ `ESP32_X509.ino` - Code chính cho ESP32
- ✅ `esp32_certs.h` - Header chứa certificates

## 🚀 Hướng Dẫn Sử Dụng

### Bước 1: Sinh Certificates

```bash
# Cài đặt thư viện Python
pip install cryptography

# Chỉnh sửa MAC address trong gen_certs.py
# Dòng 14: DEVICE_MAC = "A842E3578AD4"  # Thay bằng MAC của ESP32

# Chạy script
python gen_certs.py
```

**Kết quả:**
- Tạo thư mục `certs/` và `tb_ssl/`
- Sinh CA certificate và device certificates

### Bước 2: Cấu Hình ThingsBoard

1. **Start ThingsBoard:**
```bash
docker-compose up -d
```

2. **Truy cập ThingsBoard UI:**
   - URL: `http://localhost:8080`
   - Username: `tenant@thingsboard.org`
   - Password: `tenant`

3. **Tạo Device Profile với X.509:**
   - Vào **Device profiles** → **Add new profile**
   - Name: `ESP32_X509`
   - Transport type: `MQTT`
   - Bật **X.509 certificate chain**
   - Paste nội dung file `certs/root_ca.pem` vào ô **Certificate in PEM format**
   - Save

### Bước 3: Cập Nhật ESP32 Code

1. **Mở file `esp32_certs.h`**

2. **Copy certificates:**
   - Copy nội dung `certs/root_ca.pem` → `ca_cert`
   - Copy nội dung `certs/{MAC_ADDRESS}.crt` → `device_cert`
   - Copy nội dung `certs/{MAC_ADDRESS}.key` → `device_key`

3. **Mở file `ESP32_X509.ino`**

4. **Cập nhật WiFi và ThingsBoard:**
```cpp
const char* ssid = "TEN_WIFI_CUA_BAN";
const char* password = "MAT_KHAU_WIFI";
const char* mqtt_server = "IP_THINGSBOARD";  // VD: "192.168.1.100"
```

5. **Upload code lên ESP32**

### Bước 4: Kiểm Tra Kết Nối

1. **Mở Serial Monitor** (115200 baud)

2. **Xem log kết nối:**
```
🌐 Connecting to WiFi...
✅ WiFi connected
📍 IP address: 192.168.1.123
📱 MAC address: A842E3578AD4
🔐 Loading certificates...
✅ Certificates loaded
🔌 Attempting MQTT connection...
✅ Connected to ThingsBoard!
📤 Sending telemetry: {"temperature":25,"humidity":50,"uptime":10}
```

3. **Kiểm tra ThingsBoard:**
   - Vào **Devices** → Sẽ thấy device mới với tên = MAC address
   - Click vào device → **Latest telemetry** → Xem dữ liệu

## 🔒 Bảo Mật

### ⚠️ FILE QUAN TRỌNG - KHÔNG GỬI ĐI:
- ❌ `certs/root_ca.key` - CA private key (giữ bí mật!)
- ❌ `certs/{MAC_ADDRESS}.key` - Device private key (chỉ flash vào ESP32)

### ✅ FILE CÓ THỂ CHIA SẺ:
- ✅ `certs/root_ca.pem` - Paste vào ThingsBoard
- ✅ `certs/{MAC_ADDRESS}.crt` - Device certificate

## 🧪 Flow Hoạt Động

```
1. gen_certs.py → Sinh certificates
         ↓
2. root_ca.pem → Paste vào ThingsBoard Device Profile
         ↓
3. docker-compose up -d → Chạy ThingsBoard
         ↓
4. esp32_certs.h → Nhúng certs vào ESP32
         ↓
5. ESP32 connect → TLS handshake
         ↓
6. ThingsBoard verify cert → Auto-create device (tên = MAC)
         ↓
7. MQTT data → Telemetry hiển thị trên dashboard
```

## 🐛 Troubleshooting

### ESP32 không kết nối được:

1. **Kiểm tra certificates:**
   - Đảm bảo đã copy đúng nội dung (bao gồm `-----BEGIN...-----` và `-----END...-----`)
   - Kiểm tra MAC address trong `gen_certs.py` khớp với ESP32

2. **Kiểm tra ThingsBoard:**
   - Device Profile đã paste đúng `root_ca.pem`
   - MQTT SSL port 8883 đã mở

3. **Kiểm tra network:**
   - ESP32 và ThingsBoard cùng mạng
   - Firewall không block port 8883

### Error "MQTT_CONNECT_UNAUTHORIZED":
- Certificates không khớp
- ThingsBoard chưa có Device Profile với CA cert
- CN trong device cert không khớp với MAC address

## 📊 Cấu Trúc Thư Mục

```
day12/
├── docker-compose.yml          # ThingsBoard container
├── gen_certs.py               # Script sinh certs
├── ESP32_X509.ino            # ESP32 firmware
├── esp32_certs.h             # ESP32 certificates header
├── README.md                 # File này
├── certs/                    # Certificates (auto-generated)
│   ├── root_ca.pem
│   ├── root_ca.key
│   ├── A842E3578AD4.crt
│   └── A842E3578AD4.key
└── tb_ssl/                   # ThingsBoard SSL (auto-generated)
    └── rootCert.pem
```

## 🎯 Tổng Kết

**6 FILE TỐI THIỂU:**
1. ✅ `docker-compose.yml`
2. ✅ `gen_certs.py`
3. ✅ `root_ca.pem` (generated)
4. ✅ `{MAC}.crt` (generated)
5. ✅ `esp32_certs.h`
6. ✅ `ESP32_X509.ino`

**Thời gian setup:** ~10 phút

**Kết quả:** ESP32 tự động tạo device trên ThingsBoard và gửi data qua MQTT SSL! 🎉
