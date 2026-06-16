# Irrigation Gateway v1 - Threaded Architecture Update

## Overview
Đã cập nhật gateway từ kiến trúc single-threaded sang multi-threaded để hỗ trợ xử lý đồng thời LoRa communication và AI decision making.

## Key Changes

### 1. Threading Architecture
- **LoRa Thread**: Xử lý tất cả communication LoRa với ưu tiên cao
- **AI Thread**: Chạy song song để xử lý AI tasks (plant classification, irrigation decisions)
- **Main Thread**: Giám sát health check và quản lý shutdown

### 2. AI Integration
- **Plant Classification**: YOLOv8 chạy hàng ngày lúc 8:00 AM để phân loại giai đoạn cây trồng
- **Irrigation Decisions**: Rule-based AI quyết định tưới tiêu mỗi 15 phút
- **User Confirmation**: Hệ thống xác nhận từ người dùng khi AI không chắc chắn

### 3. Enhanced MQTT Communication
- Thêm các topic mới cho irrigation requests và confirmations
- Publish plant stage classification results
- Handle user confirmations với timeout 5 phút

### 4. Improved State Management
- `latest_telemetry`: Lưu trữ dữ liệu cảm biến mới nhất cho AI decisions
- `node_online`: Theo dõi trạng thái kết nối của node
- `current_plant_stage`: Lưu trữ giai đoạn cây trồng hiện tại

## Thread Operations

### LoRa Worker Thread
- Xử lý nhận telemetry từ node
- Gửi ACK responses
- Xử lý commands từ MQTT
- Quản lý pending commands queue
- Check user confirmation timeouts

### AI Worker Thread
- Plant classification hàng ngày lúc 8:00 AM
- Irrigation decisions mỗi 15 phút
- Tích hợp với rule-based AI và user confirmation logic

## Configuration
- YOLO model path: `YOLO_MODEL_PATH`
- MQTT broker settings
- LoRa frequency: 433MHz
- Threading với daemon threads cho graceful shutdown

## Dependencies
- `threading`: Multi-threading support
- `queue`: Thread-safe communication
- `ultralytics`: YOLOv8 for plant classification
- `opencv-python`: Camera processing
- `adafruit-circuitpython-rfm9x`: LoRa communication

## Usage
```python
gateway = IrrigationGateway()
gateway.run()  # Starts all threads and begins operation
```

## Error Handling
- Thread exceptions được log và không làm crash toàn bộ hệ thống
- Health checks định kỳ cho MQTT và LoRa connections
- Node timeout detection và offline notifications