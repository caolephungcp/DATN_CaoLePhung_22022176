# Hướng dẫn setup & chạy Gateway trên Raspberry Pi4

## 1. Chuẩn bị phần cứng

### LoRa RA01 Module
- NSS: GPIO10 (hoặc CE1)
- SCLK: GPIO11
- MISO: GPIO9
- MOSI: GPIO10
- RST: GPIO25 (hoặc board.D25)
- DIO0: GPIO24 (hoặc board.D24)

### Camera
- USB camera hoặc Pi Camera v2
- Nếu dùng Pi Camera, enable trong raspi-config

### Kết nối MQTT
- ThingBoard server IP + port 1883
- Device token (lấy từ dashboard)

---

## 2. Setup Pi4

```bash
# Update system
sudo apt update
sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3-pip python3-dev libjpeg-dev zlib1g-dev
sudo apt install -y libatlas-base-dev libjasper-dev libharfbuzz0b libwebp6 libtiff5
sudo apt install -y libhyphen0 libraqm0

# Enable SPI + I2C
sudo raspi-config
# -> Interfacing Options -> SPI -> Enable
# -> Interfacing Options -> I2C -> Enable
```

---

## 3. Install Python packages

```bash
cd /path/to/gateway

# Tạo virtual environment (tuỳ chọn nhưng khuyến nghị)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Download YOLOv8 model (lần đầu chỉ)
python3 -c "from ultralytics import YOLO; YOLO('yolov8s-cls.pt')"
```

---

## 4. Cấu hình Gateway

Mở file `Irrigation_Gateway_Pi4_v1.py` và cập nhật:

```python
# MQTT settings
MQTT_BROKER = "192.168.1.100"  # IP của ThingBoard server
MQTT_PORT = 1883
MQTT_USER = "device_token"     # Từ ThingBoard dashboard
MQTT_PASS = ""

# LoRa pins (tuỳ theo board)
LORA_CS = digitalio.DigitalInOut(board.CE1)
LORA_RST = digitalio.DigitalInOut(board.D25)
LORA_DIO0 = digitalio.DigitalInOut(board.D24)

# YOLOv8 schedule
YOLO_SCHEDULE_TIME = "08:00"  # Chạy 8:00 sáng

# Camera index
CAMERA_INDEX = 0  # 0 = USB camera, 0 = Pi camera

# File paths
IMAGE_SAVE_PATH = "/home/pi/gateway_images"
LOG_FILE = "/home/pi/gateway.log"  # hoặc /var/log/irrigation_gateway.log
```

---

## 5. Chạy Gateway

### Option A: Test chạy trực tiếp
```bash
python3 Irrigation_Gateway_Pi4_v1.py
```

### Option B: Chạy background (tmux/screen)
```bash
tmux new-session -d -s gateway "python3 Irrigation_Gateway_Pi4_v1.py"

# View logs
tmux attach-session -t gateway

# Kill
tmux kill-session -t gateway
```

### Option C: Chạy với systemd (tự động boot)
```bash
# Tạo service file
sudo nano /etc/systemd/system/irrigation-gateway.service
```

Paste nội dung:
```ini
[Unit]
Description=Irrigation Gateway
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/irrigation_gateway
ExecStart=/home/pi/irrigation_gateway/venv/bin/python3 Irrigation_Gateway_Pi4_v1.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Rồi chạy:
```bash
sudo systemctl daemon-reload
sudo systemctl enable irrigation-gateway
sudo systemctl start irrigation-gateway

# View status
sudo systemctl status irrigation-gateway

# View logs
sudo journalctl -u irrigation-gateway -f
```

---

## 6. Kiểm tra bộ xử lý

### Check LoRa
```bash
python3 -c "
try:
    import board
    import busio
    import digitalio
    import adafruit_rfm9x
    i2c = busio.I2C(board.SCL, board.SDA)
    rfm9x = adafruit_rfm9x.RFM9x(i2c, digitalio.DigitalInOut(board.CE1), 433.0)
    print('LoRa OK!')
except Exception as e:
    print(f'LoRa ERROR: {e}')
"
```

### Check Camera
```bash
python3 -c "
import cv2
cap = cv2.VideoCapture(0)
if cap.isOpened():
    print('Camera OK!')
    cap.release()
else:
    print('Camera ERROR!')
"
```

### Check MQTT
```bash
python3 -c "
import paho.mqtt.client as mqtt
client = mqtt.Client()
client.connect('192.168.1.100', 1883, 60)
print('MQTT OK!')
client.disconnect()
"
```

### Check YOLOv8
```bash
python3 -c "
from ultralytics import YOLO
model = YOLO('yolov8s-cls.pt')
print('YOLOv8 OK!')
"
```

---

## 7. Log files

```bash
# Logs của gateway
tail -f /home/pi/gateway.log
# hoặc
tail -f /var/log/irrigation_gateway.log

# Systemd logs
journalctl -u irrigation-gateway -f --all
```

---

## 8. Troubleshooting

### MQTT không kết nối
- Check IP + port ThingBoard
- Check device token
- Kiểm tra firewall

### LoRa không nhận dữ liệu
- Check wiring pins
- Kiểm tra tần số (433MHz)
- Reset module
- Check node gửi dữ liệu

### YOLOv8 chạy chậm / Pi nóng
- Giảm image size
- Dùng model nhẹ hơn (yolov8n-cls)
- Tăng schedule interval (2x/ngày thay vì 1x)

### Camera không capture
```bash
v4l2-ctl --list-devices  # Xem camera available
```

---

## 9. Cấu trúc dữ liệu

### Node telemetry (LoRa RX)
```
Format: gate01-node01-pump-1-valve-0-soil1-35.2-soil2-38.1-ph1-6.7-ph2-6.9-override-0
```

### Command từ server (MQTT RX)
```json
{
  "method": "control_pump",
  "params": {"pump": 1}
}
```

### Telemetry gửi lên server (MQTT TX)
```json
{
  "node": "node01",
  "pump": 1,
  "valve": 0,
  "soil1": 35.2,
  "soil2": 38.1,
  "ph1": 6.7,
  "ph2": 6.9,
  "override": 0,
  "rssi": -85,
  "snr": 8
}
```

### YOLOv8 event
```json
{
  "event": "yolo_inference",
  "class": "dry",
  "confidence": 0.92,
  "image_path": "/home/pi/gateway_images/yolo_20240403_080000.jpg"
}
```

---

## 10. Performance Tips

- **LoRa timeout**: Tăng `CMD_ACK_TIMEOUT` nếu RF yếu
- **MQTT**: Dùng QoS=0 nếu không cần đảm bảo
- **YOLOv8**: Dùng `yolov8n-cls` (nano) thay vì `s-cls` (small) nếu Pi chậm
- **Camera**: Giảm fps (15-20) thay vì 30

---

Enjoy! 🎉
