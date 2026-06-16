# ============================================================================
# IRRIGATION GATEWAY MODULES
# ============================================================================

"""
Irrigation Gateway - Raspberry Pi4
Chức năng:
  1. Nhận telemetry từ Node qua LoRa
  2. Forward lên Server (ThingBoard) qua MQTT
  3. Nhận commands từ Server qua MQTT
  4. Gửi commands xuống Node qua LoRa
  5. Chạy YOLOv8-cls 1 lần/ngày để phân loại trạng thái cây
"""

__version__ = "1.0.0"
__author__ = "Irrigation Gateway Team"

# Import main components for easy access
from .config import *
from .logger import logger
from .data_structures import *
from .lora_handler import LoRaHandler
from .mqtt_handler import MQTTHandler
from .ai_handler import AIHandler
from .irrigation_gateway import IrrigationGateway
from .main import main

__all__ = [
    # Config
    'GATEWAY_ID', 'NODE_ID', 'MQTT_BROKER', 'MQTT_PORT', 'MQTT_USER', 'MQTT_PASS',
    'LORA_FREQ', 'YOLO_MODEL_PATH', 'CAMERA_INDEX', 'IMAGE_SAVE_PATH',

    # Logger
    'logger',

    # Data structures
    'NodeStatus', 'PendingCommand', 'YOLOEvent', 'IrrigationDecision',
    'IrrigationEvent', 'UserConfirmation',

    # Handlers
    'LoRaHandler', 'MQTTHandler', 'AIHandler',

    # Main gateway
    'IrrigationGateway',

    # Entry point
    'main'
]