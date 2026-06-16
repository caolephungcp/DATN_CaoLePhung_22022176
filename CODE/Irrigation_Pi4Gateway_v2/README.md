# Irrigation Gateway - Modular Architecture

## Overview
Hệ thống gateway tưới tiêu thông minh với kiến trúc module để dễ quản lý và bảo trì.

## Cấu trúc thư mục

```
Irrigation_Pi4Gateway_v1/
├── modules/                    # Các module chính
│   ├── __init__.py            # Package initialization
│   ├── config.py              # Cấu hình hệ thống
│   ├── logger.py              # Setup logging
│   ├── data_structures.py     # Định nghĩa data structures
│   ├── lora_handler.py        # Xử lý LoRa communication
│   ├── mqtt_handler.py        # Xử lý MQTT communication
│   ├── ai_handler.py          # Xử lý AI (YOLO, irrigation decisions)
│   ├── irrigation_gateway.py  # Main gateway class
│   └── main.py                # Entry point với threading
├── run.py                     # Script chạy gateway
├── requirements.txt           # Python dependencies
└── README.md                  # Tài liệu này
```

## Cài đặt

### 1. Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### 2. Cấu hình
Chỉnh sửa file `modules/config.py` để cấu hình:
- Thông tin MQTT (broker, token)
- Cấu hình LoRa (frequency, pins)
- Đường dẫn YOLO model
- Cấu hình camera

## Chạy Gateway

### Cách 1: Chạy trực tiếp
```bash
python run.py
```

### Cách 2: Import module
```python
from modules import IrrigationGateway

gateway = IrrigationGateway()
gateway.run()
```

## Các Module

### 1. config.py
Chứa tất cả cấu hình hệ thống:
- MQTT settings
- LoRa settings
- YOLO settings
- Node settings

### 2. logger.py
Thiết lập logging với file và console output.

### 3. data_structures.py
Định nghĩa các class data:
- `NodeStatus`: Trạng thái node
- `PendingCommand`: Lệnh đang chờ
- `YOLOEvent`: Kết quả YOLO classification
- `IrrigationDecision`: Quyết định tưới tiêu
- `IrrigationEvent`: Sự kiện tưới tiêu
- `UserConfirmation`: Xác nhận từ user

### 4. lora_handler.py
Xử lý communication LoRa với node:
- Gửi/nhận dữ liệu
- ACK handling
- Error handling

### 5. mqtt_handler.py
Xử lý communication MQTT với server:
- Publish telemetry
- Receive commands
- RPC responses
- Irrigation notifications

### 6. ai_handler.py
Xử lý AI tasks:
- YOLO plant stage classification
- Rule-based irrigation decisions
- Camera capture và image processing

### 7. irrigation_gateway.py
Main gateway class tích hợp tất cả modules:
- Threading management
- State management
- Command processing
- Health monitoring

### 8. main.py
Entry point với threading setup:
- LoRa thread: Xử lý communication
- Scheduler thread: Xử lý AI và scheduling
- Main thread: Health monitoring

## Threading Architecture

Gateway sử dụng 3 threads:

1. **LoRa Thread**: Ưu tiên cao
   - Nhận telemetry từ node
   - Xử lý commands từ MQTT
   - Gửi commands tới node
   - ACK handling

2. **AI/Scheduler Thread**: Chạy song song
   - YOLO classification (8:00 AM daily)
   - Irrigation decisions (every 15 min)
   - Health checks

3. **Main Thread**: Giám sát
   - Health monitoring
   - Graceful shutdown

## API Usage

### Khởi tạo Gateway
```python
from modules import IrrigationGateway

gateway = IrrigationGateway()
```

### Custom Configuration
```python
from modules import MQTTHandler, LoRaHandler, AIHandler

# Custom MQTT
mqtt = MQTTHandler(broker="custom.broker.com", port=1883)

# Custom LoRa
lora = LoRaHandler()

# Custom AI
ai = AIHandler(yolo_model_path="custom_model.pt")
```

### Manual Control
```python
# Start gateway
gateway.start()

# Stop gateway
gateway.stop()
```

## Development

### Thêm Module mới
1. Tạo file trong `modules/`
2. Import trong `__init__.py`
3. Update documentation

### Testing
```bash
# Test individual modules
python -c "from modules.lora_handler import LoRaHandler; print('LoRa OK')"

# Test full gateway
python run.py
```

## Troubleshooting

### Import Errors
```bash
# Install missing packages
pip install paho-mqtt adafruit-circuitpython-rfm9x opencv-python ultralytics
```

### LoRa Issues
- Check GPIO pin configuration in `config.py`
- Verify SPI interface enabled on Raspberry Pi
- Check antenna connection

### MQTT Issues
- Verify broker URL and credentials
- Check network connectivity
- Review firewall settings

### Camera Issues
- Verify camera connected and enabled
- Check OpenCV installation
- Test camera with `cv2.VideoCapture(0)`

## License
[Your License Here]