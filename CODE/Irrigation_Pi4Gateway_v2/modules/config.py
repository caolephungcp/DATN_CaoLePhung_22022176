# ============================================================================
# CONFIGURATION
# ============================================================================

import os

# LoRa pins (Customize theo hardware)
LORA_CS_PIN = 7  # GPIO pin for CS
LORA_RST_PIN = 25  # GPIO pin for RST
LORA_DIO0_PIN = 24  # GPIO pin for DIO0

# LoRa settings
LORA_FREQ = 433.0  # MHz
LORA_BAUD = 9600

# MQTT settings
THINGSBOARD_HOST = 'thingsboard.cloud'
ACCESS_TOKEN = 'sd2j412m5779ypgntmnl'

MQTT_BROKER = THINGSBOARD_HOST
MQTT_PORT = 1883
MQTT_USER = ACCESS_TOKEN  # Sử dụng ACCESS_TOKEN làm username
MQTT_PASS = ""  # Không cần password cho ThingBoard Cloud
MQTT_TIMEOUT = 60

# Node settings
GATEWAY_ID = "gate01"
NODE_ID = "node01"
NODE_TIMEOUT = 900  # 15 phút 
HEARTBEAT_CHECK = 60  # 1 phút

# Command settings
CMD_ACK_TIMEOUT = 10  # giây
CMD_RETRY_MAX = 3
ROLLBACK_FLAG = False

# YOLOv8 settings
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
YOLO_SCHEDULE_TIME = "08:00"  # Format HH:MM (8:00 sáng)
YOLO_MODEL_PATH = os.path.join(BASE_DIR, "best.onnx")
CAMERA_INDEX = 0
IMAGE_SAVE_PATH = os.path.join(os.path.expanduser("~"), "gateway_images")

# Logging
LOG_FILE = os.path.join(os.path.expanduser("~"), "gateway.log")
LOG_LEVEL = "INFO"