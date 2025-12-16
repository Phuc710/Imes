# ESP32 OCR Setup Guide

## Current Setup Status
✅ Python API: Updated to save images and return timestamps  
✅ ESP32 Code: Updated to send images to OCR API and post results to ThingsBoard  
❌ ESP32 Connection: Currently failing - "Connection failed" error

## Issues to Resolve

### 1. Network Connectivity Issue
**Problem**: ESP32 cannot connect to server at `192.168.1.71:8000`

**Troubleshooting Steps**:

#### Step 1: Verify Server IP
Check your actual server IP address:
```powershell
ipconfig
```
Look for IPv4 Address (typically 192.168.x.x)

Update if needed in both files:
- `esp32_cam_ocr.ino`: Line 111 - `const char* host = "192.168.1.71";`
- `day3/test.py`: Line 8 - `url = "http://localhost:8000/api/v1/ocr?camera_id=2"`

#### Step 2: Verify Server is Running
Start the Python server:
```powershell
cd C:\Users\Phucx\Desktop\imes\lp-ocr-api
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

You should see:
```
INFO:     Application startup complete
```

#### Step 3: Test Server from ESP32's Network
Test using the `day3/test.py` script with correct server IP:
```powershell
cd C:\Users\Phucx\Desktop\imes\day3
python .\test.py
```

Expected output (if server is running):
```
Status code: 200
Response text: {"text": "recognized text", "timestamp": "2025-12-16 09:33:39"}
```

#### Step 4: Check ESP32 WiFi Connection
The ESP32 serial output should show:
```
WiFi connected
IP: 192.168.1.xxx
```

Make sure ESP32 is on the same network as the server!

## Python API Changes

### File: `app/api/v1/schemas.py`
- Added `timestamp` field to OCRResponse

### File: `app/api/v1/routes_ocr.py`
- Creates `lp-ocr-api/img` folder automatically
- Saves images as: `ocr_{camera_id}_{timestamp}.jpg`
- Returns both `text` and `timestamp` in response

## ESP32 Code Flow

1. **Capture**: Image captured every 10 seconds
2. **Send**: Sends as multipart/form-data to `/api/v1/ocr?camera_id=2`
3. **Receive**: Gets JSON response with OCR text and timestamp
4. **Post to ThingsBoard**: 
   - URL: `http://192.168.1.71:8080/api/v1/ZA88bSL1qLkzuzEI2t0G/telemetry`
   - Payload: `{"ocr_text": "...", "ocr_time": ..., "status": "online"}`

## Testing Checklist

- [ ] Server IP is correct (verify with `ipconfig`)
- [ ] Server is running on port 8000
- [ ] ESP32 WiFi is connected to same network
- [ ] Test Python script works with correct server IP
- [ ] Serial monitor shows "Connected to server" message
- [ ] Image files appear in `lp-ocr-api/img/` folder
- [ ] ThingsBoard receives telemetry data

## Common Issues

| Error | Cause | Solution |
|-------|-------|----------|
| Connection failed | Wrong IP address | Verify with `ipconfig` |
| Connection failed | Server not running | Start uvicorn server |
| Connection failed | Different network | Put ESP32 on same WiFi |
| No images saved | Permission issue | Check folder permissions |
| Images saved but no ThingsBoard | Wrong TB IP/token | Check config.py and TB settings |

## Next Steps

1. Verify the server IP with `ipconfig`
2. Update ESP32 code with correct IP if needed
3. Start the Python server
4. Upload ESP32 code
5. Monitor serial output for connection success
6. Check `lp-ocr-api/img/` folder for saved images
