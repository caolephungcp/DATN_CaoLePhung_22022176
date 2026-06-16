#!/usr/bin/env python3
"""
Irrigation Gateway - Raspberry Pi4
Chức năng:
  1. Nhận telemetry từ Node qua LoRa
  2. Forward lên Server (ThingBoard) qua MQTT
  3. Nhận commands từ Server qua MQTT
  4. Gửi commands xuống Node qua LoRa
  5. Chạy YOLOv8-cls 1 lần/ngày để phân loại trạng thái cây
"""

import time
import json
import logging
import threading
import queue
from datetime import datetime, time as dt_time
from typing import Dict, List, Optional, Tuple

try:
    import paho.mqtt.client as mqtt
    import board
    import busio
    import digitalio
    from PIL import Image
    import cv2
    from ultralytics import YOLO
except ImportError as e:
    print(f"Import error: {e}")
    print("Install required packages:")
    print("  pip install paho-mqtt adafruit-circuitpython-rfm9x pillow opencv-python ultralytics")
    exit(1)

# ============================================================================
# CONFIG
# ============================================================================

# LoRa pins (Customize theo hardware)
LORA_CS = digitalio.DigitalInOut(board.CE0)
LORA_RST = digitalio.DigitalInOut(board.D25)
LORA_DIO0 = digitalio.DigitalInOut(board.D24)

# LoRa settings
LORA_FREQ = 433.0  # MHz
LORA_BAUD = 9600

# MQTT settings
THINGSBOARD_HOST = 'thingsboard.cloud'
ACCESS_TOKEN = '0TKA1YktXmZ96Nq7dnMr'

MQTT_BROKER = THINGSBOARD_HOST
MQTT_PORT = 1883
MQTT_USER = ACCESS_TOKEN  # Sử dụng ACCESS_TOKEN làm username
MQTT_PASS = ""  # Không cần password cho ThingBoard Cloud
MQTT_TIMEOUT = 60

# Node settings
GATEWAY_ID = "gate01"
NODE_ID = "node01"
NODE_TIMEOUT = 900  # 15 phút (giây)
HEARTBEAT_CHECK = 60  # mỗi 1 phút check health

# Command settings
CMD_ACK_TIMEOUT = 2  # giây
CMD_RETRY_MAX = 3

# YOLOv8 settings
YOLO_SCHEDULE_TIME = "08:00"  # Format HH:MM (8:00 sáng)
YOLO_MODEL_PATH = "yolov8s-cls.pt"
CAMERA_INDEX = 0
IMAGE_SAVE_PATH = "/home/pi/gateway_images"

# Logging
LOG_FILE = "/var/log/irrigation_gateway.log"
LOG_LEVEL = logging.INFO

# ============================================================================
# LOGGING
# ============================================================================

def setup_logging():
    logger = logging.getLogger("GatewayPi4")
    logger.setLevel(LOG_LEVEL)
    
    # File handler
    try:
        fh = logging.FileHandler(LOG_FILE)
    except:
        fh = logging.FileHandler("gateway.log")
    fh.setLevel(LOG_LEVEL)
    
    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(LOG_LEVEL)
    
    # Formatter
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)
    
    return logger

logger = setup_logging()

# ============================================================================
# DATA STRUCTURES
# ============================================================================

class NodeStatus:
    def __init__(self, node_id):
        self.node_id = node_id
        self.pump = False
        self.valve = False
        self.soil1 = 0.0
        self.soil2 = 0.0
        self.temp1 = 0.0
        self.temp2 = 0.0
        self.ph1 = 0.0
        self.ph2 = 0.0
        self.override = False
        self.last_update = 0
        self.rssi = 0
        self.snr = 0
        self.frame_count = 0

class PendingCommand:
    def __init__(self, node_id, action, params, rpc_id=None):
        self.node_id = node_id
        self.action = action  # "control_pump", "control_valve", etc.
        self.params = params  # {"pump": 1, "duration": 300}
        self.rpc_id = rpc_id
        self.ts = time.time()
        self.send_ts = None
        self.retry_count = 0

class YOLOEvent:
    def __init__(self, class_name, confidence, image_path=None):
        self.timestamp = time.time()
        self.class_name = class_name  # 'dry', 'healthy', 'pest', 'weed'
        self.confidence = confidence
        self.image_path = image_path

class IrrigationDecision:
    """Quyết định tưới nước"""
    IRRIGATE = "irrigate"  # Tưới ngay
    ASK_USER = "ask_user"  # Hỏi ý kiến người dùng
    NO_IRRIGATE = "no_irrigate"  # Không tưới

class IrrigationEvent:
    def __init__(self, decision: str, confidence: float, reason: str, sensor_data: dict = None):
        self.timestamp = time.time()
        self.decision = decision
        self.confidence = confidence
        self.reason = reason
        self.sensor_data = sensor_data or {}

class UserConfirmation:
    def __init__(self, event_id: str, decision: str, timeout: int = 300):
        self.event_id = event_id
        self.decision = decision  # "irrigate" or "no_irrigate"
        self.timestamp = time.time()
        self.timeout = timeout

# ============================================================================
# LORA HANDLER
# ============================================================================

class LoRaHandler:
    def __init__(self):
        self.initialized = False
        self.last_rssi = 0
        self.last_snr = 0
        try:
            import adafruit_rfm9x
            spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
            self.rfm9x = adafruit_rfm9x.RFM9x(spi, LORA_CS, LORA_RST, LORA_FREQ)
            self.rfm9x.tx_power = 23
            self.initialized = True
            logger.info("LoRa initialized successfully")
        except Exception as e:
            logger.error(f"LoRa initialization failed: {e}")
            self.initialized = False
    
    def send(self, data: str) -> bool:
        """Gửi dữ liệu qua LoRa"""
        if not self.initialized:
            logger.warning("LoRa not initialized, cannot send")
            return False
        try:
            self.rfm9x.send(data.encode('utf-8'))
            logger.debug(f"LoRa TX: {data}")
            return True
        except Exception as e:
            logger.error(f"LoRa send failed: {e}")
            return False
    
    def receive(self, timeout=0.1) -> Optional[str]:
        """Nhận dữ liệu từ LoRa"""
        if not self.initialized:
            return None
        try:
            packet = self.rfm9x.receive(timeout=timeout)
            if packet is not None:
                self.last_rssi = self.rfm9x.last_rssi
                self.last_snr = self.rfm9x.last_snr
                data = packet.decode('utf-8')
                logger.debug(f"LoRa RX: {data} (RSSI: {self.last_rssi}, SNR: {self.last_snr})")
                return data
        except Exception as e:
            logger.warning(f"LoRa receive error: {e}")
        return None
    
    def reset(self):
        """Reset LoRa module"""
        logger.info("Resetting LoRa module...")
        try:
            if self.initialized:
                self.rfm9x.reset()
                time.sleep(0.5)
                logger.info("LoRa reset successful")
        except Exception as e:
            logger.warning(f"LoRa reset failed: {e}")

# ============================================================================
# MQTT HANDLER
# ============================================================================

class MQTTHandler:
    def __init__(self, broker, port, user, password):
        self.broker = broker
        self.port = port
        self.user = user
        self.password = password
        self.client = mqtt.Client(client_id="gateway_pi4")
        self.connected = False
        self.command_queue = Queue()
        self.rpc_callbacks = {}
        
        # Callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
    
    def connect(self) -> bool:
        """Kết nối MQTT"""
        try:
            if self.user:
                self.client.username_pw_set(self.user, self.password)
            self.client.connect(self.broker, self.port, MQTT_TIMEOUT)
            self.client.loop_start()
            logger.info(f"MQTT connecting to {self.broker}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"MQTT connection failed: {e}")
            return False
    
    def disconnect(self):
        """Ngắt kết nối MQTT"""
        try:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False
            logger.info("MQTT disconnected")
        except Exception as e:
            logger.warning(f"MQTT disconnect error: {e}")
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback khi kết nối thành công"""
        if rc == 0:
            self.connected = True
            logger.info("MQTT connected")
            # Subscribe to command topics
            client.subscribe("v1/devices/me/rpc/request/+")
            client.subscribe("v1/devices/me/attributes")
        else:
            logger.error(f"MQTT connection failed: code {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback khi ngắt kết nối"""
        self.connected = False
        logger.warning(f"MQTT disconnected: code {rc}")
    
    def _on_message(self, client, userdata, msg):
        """Callback khi nhận message"""
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode('utf-8'))
            
            logger.debug(f"MQTT message: {topic} -> {payload}")
            
            # RPC command
            if "rpc/request" in topic:
                rpc_id = topic.split("/")[-1]
                self.command_queue.put((payload, rpc_id))
            
            # Attributes
            elif "attributes" in topic:
                logger.debug(f"Attributes updated: {payload}")
        except Exception as e:
            logger.error(f"MQTT message parsing error: {e}")
    
    def publish_telemetry(self, data: dict) -> bool:
        """Gửi telemetry lên server"""
        try:
            payload = json.dumps(data)
            self.client.publish("v1/devices/me/telemetry", payload)
            logger.debug(f"Telemetry published: {payload}")
            return True
        except Exception as e:
            logger.error(f"Telemetry publish failed: {e}")
            return False
    
    def publish_rpc_response(self, rpc_id: str, response: dict) -> bool:
        """Trả lời RPC response"""
        try:
            payload = json.dumps(response)
            topic = f"v1/devices/me/rpc/response/{rpc_id}"
            self.client.publish(topic, payload)
            logger.debug(f"RPC response published: {response}")
            return True
        except Exception as e:
            logger.error(f"RPC response publish failed: {e}")
            return False
    
    def get_command(self) -> Optional[tuple]:
        """Lấy command từ queue"""
        try:
            return self.command_queue.get_nowait()
        except:
            return None
    
    def publish_irrigation_request(self, decision) -> bool:
        """Gửi yêu cầu xác nhận tưới tiêu tới user"""
        try:
            payload = json.dumps({
                "event": "irrigation_request",
                "decision_id": decision.id,
                "duration": decision.duration,
                "reason": decision.reason,
                "confidence": decision.confidence,
                "plant_stage": decision.plant_stage,
                "sensor_data": decision.sensor_data
            })
            self.client.publish("v1/devices/me/irrigation/request", payload)
            logger.info(f"Irrigation request published: {decision.id}")
            return True
        except Exception as e:
            logger.error(f"Irrigation request publish failed: {e}")
            return False
    
    def publish_irrigation_decision(self, decision) -> bool:
        """Gửi quyết định tưới tiêu đã thực hiện"""
        try:
            payload = json.dumps({
                "event": "irrigation_decision",
                "decision_id": decision.id,
                "duration": decision.duration,
                "reason": decision.reason,
                "executed": True
            })
            self.client.publish("v1/devices/me/irrigation/decision", payload)
            logger.info(f"Irrigation decision published: {decision.id}")
            return True
        except Exception as e:
            logger.error(f"Irrigation decision publish failed: {e}")
            return False
    
    def publish_confirmation_result(self, decision_id: str, approved: bool) -> bool:
        """Gửi kết quả xác nhận từ user"""
        try:
            payload = json.dumps({
                "event": "confirmation_result",
                "decision_id": decision_id,
                "approved": approved
            })
            self.client.publish("v1/devices/me/irrigation/confirmation", payload)
            logger.info(f"Confirmation result published: {decision_id}, approved={approved}")
            return True
        except Exception as e:
            logger.error(f"Confirmation result publish failed: {e}")
            return False

# ============================================================================
# AI HANDLER
# ============================================================================

class AIHandler:
    def __init__(self, yolo_model_path: str, irrigation_model_path: str = None):
        self.yolo_model = None
        self.irrigation_model = None  # Placeholder for future irrigation model
        self.camera = None
        self.initialized = False
        
        try:
            # Load YOLOv8 classification model
            logger.info(f"Loading YOLOv8 model: {yolo_model_path}")
            self.yolo_model = YOLO(yolo_model_path)
            
            # Initialize camera
            logger.info(f"Initializing camera: {CAMERA_INDEX}")
            self.camera = cv2.VideoCapture(CAMERA_INDEX)
            if not self.camera.isOpened():
                logger.error("Camera failed to open")
                return
            
            # TODO: Load irrigation model when available
            # self.irrigation_model = load_irrigation_model(irrigation_model_path)
            
            self.initialized = True
            logger.info("AI Handler initialized successfully")
        except Exception as e:
            logger.error(f"AI Handler initialization failed: {e}")
    
    def capture_image(self) -> Optional[str]:
        """Chụp ảnh từ camera"""
        if not self.camera or not self.camera.isOpened():
            logger.error("Camera not available")
            return None
        
        try:
            ret, frame = self.camera.read()
            if not ret:
                logger.error("Failed to capture image")
                return None
            
            # Save image
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_path = f"{IMAGE_SAVE_PATH}/capture_{timestamp}.jpg"
            
            # Ensure directory exists
            import os
            os.makedirs(IMAGE_SAVE_PATH, exist_ok=True)
            
            cv2.imwrite(image_path, frame)
            logger.info(f"Image captured: {image_path}")
            return image_path
        except Exception as e:
            logger.error(f"Image capture failed: {e}")
            return None
    
    def classify_plant_stage(self) -> Optional[YOLOEvent]:
        """Phân loại giai đoạn cây trồng"""
        if not self.initialized or not self.yolo_model:
            logger.error("YOLO model not available")
            return None
        
        try:
            # Capture image
            image_path = self.capture_image()
            if not image_path:
                return None
            
            # Run inference
            logger.info("Running YOLOv8 plant stage classification...")
            results = self.yolo_model(image_path)
            
            if results and len(results) > 0:
                # Get top prediction
                result = results[0]
                if result.probs is not None:
                    probs = result.probs.data.cpu().numpy()
                    class_idx = probs.argmax()
                    confidence = float(probs[class_idx])
                    
                    # Map class index to plant stage
                    class_names = ['dry', 'healthy', 'pest', 'weed', 'young', 'mature']
                    class_name = class_names[class_idx] if class_idx < len(class_names) else f"class_{class_idx}"
                    
                    event = YOLOEvent(class_name, confidence, image_path)
                    logger.info(f"Plant stage classified: {class_name} (confidence: {confidence:.2f})")
                    return event
                else:
                    logger.warning("No probabilities in YOLO result")
            else:
                logger.warning("No results from YOLO inference")
                
        except Exception as e:
            logger.error(f"YOLO inference failed: {e}")
        
        return None
    
    def decide_irrigation(self, sensor_data: dict, plant_stage: str = None) -> Optional[IrrigationEvent]:
        """Quyết định tưới nước dựa trên dữ liệu cảm biến và giai đoạn cây"""
        try:
            # Extract sensor data
            soil1 = sensor_data.get('soil1', 50.0)
            soil2 = sensor_data.get('soil2', 50.0)
            temp1 = sensor_data.get('temp1', 25.0)
            ph1 = sensor_data.get('ph1', 7.0)
            
            # Simple rule-based irrigation decision
            # TODO: Replace with trained ML model
            
            avg_soil = (soil1 + soil2) / 2
            reason = ""
            confidence = 0.0
            
            # Rule 1: Soil moisture < 30% -> Definitely irrigate
            if avg_soil < 30:
                decision = IrrigationDecision.IRRIGATE
                confidence = 0.9
                reason = f"Soil moisture too low: {avg_soil:.1f}%"
            
            # Rule 2: Soil moisture > 70% -> No irrigation needed
            elif avg_soil > 70:
                decision = IrrigationDecision.NO_IRRIGATE
                confidence = 0.8
                reason = f"Soil moisture sufficient: {avg_soil:.1f}%"
            
            # Rule 3: Temperature > 35°C and soil < 50% -> Ask user (heat stress)
            elif temp1 > 35 and avg_soil < 50:
                decision = IrrigationDecision.ASK_USER
                confidence = 0.6
                reason = f"High temperature ({temp1:.1f}°C) with moderate soil moisture ({avg_soil:.1f}%) - ask user"
            
            # Rule 4: pH out of range -> Ask user
            elif ph1 < 6.0 or ph1 > 8.0:
                decision = IrrigationDecision.ASK_USER
                confidence = 0.7
                reason = f"pH out of optimal range: {ph1:.1f} - ask user"
            
            # Rule 5: Plant stage consideration
            elif plant_stage == 'dry':
                decision = IrrigationDecision.IRRIGATE
                confidence = 0.85
                reason = f"Plant shows dry stage - irrigation needed"
            
            elif plant_stage == 'young':
                if avg_soil < 60:
                    decision = IrrigationDecision.IRRIGATE
                    confidence = 0.8
                    reason = f"Young plant needs consistent moisture: {avg_soil:.1f}%"
                else:
                    decision = IrrigationDecision.NO_IRRIGATE
                    confidence = 0.7
                    reason = f"Young plant has sufficient moisture: {avg_soil:.1f}%"
            
            # Default: Moderate conditions - ask user
            else:
                decision = IrrigationDecision.ASK_USER
                confidence = 0.5
                reason = f"Moderate conditions - user decision needed (soil: {avg_soil:.1f}%, temp: {temp1:.1f}°C)"
            
            event = IrrigationEvent(decision, confidence, reason, sensor_data)
            logger.info(f"Irrigation decision: {decision} (confidence: {confidence:.2f}) - {reason}")
            return event
            
        except Exception as e:
            logger.error(f"Irrigation decision failed: {e}")
            return None

# ============================================================================
# GATEWAY MAIN
# ============================================================================

class IrrigationGateway:
    def __init__(self):
        self.lora = LoRaHandler()
        self.mqtt = MQTTHandler(MQTT_BROKER, MQTT_PORT, MQTT_USER, MQTT_PASS)
        self.ai = AIHandler(YOLO_MODEL_PATH)
        
        self.nodes_status: Dict[str, NodeStatus] = {}
        self.pending_commands: List[PendingCommand] = []
        self.pending_confirmations: Dict[str, UserConfirmation] = {}
        
        # Threading
        self.lora_thread = None
        self.ai_thread = None
        self.running = False
        
        # Timers
        self.last_health_check = 0
        self.last_yolo_run = 0
        self.last_irrigation_check = 0
        
        self.mqtt_connected = False
        self.current_plant_stage = "unknown"
        self.latest_telemetry = None
        self.node_online = False
    
    def start(self):
        """Khởi động gateway"""
        logger.info("=== Irrigation Gateway Starting ===")
        
        # Connect MQTT
        if not self.mqtt.connect():
            logger.error("Failed to connect MQTT")
            return False
        
        # Wait for MQTT connected
        for i in range(10):
            if self.mqtt.connected:
                self.mqtt_connected = True
                break
            time.sleep(0.5)
        
        if not self.mqtt_connected:
            logger.warning("MQTT not connected, continuing anyway...")
        
        self.running = True
        logger.info("Gateway started successfully")
        return True
    
    def stop(self):
        """Dừng gateway"""
        logger.info("Stopping gateway...")
        self.running = False
        
        # Stop threads
        if self.lora_thread and self.lora_thread.is_alive():
            self.lora_thread.join(timeout=2)
        if self.ai_thread and self.ai_thread.is_alive():
            self.ai_thread.join(timeout=2)
        
        self.mqtt.disconnect()
        if self.ai.camera:
            self.ai.camera.release()
        logger.info("Gateway stopped")
    
    def lora_worker(self):
        """Luồng xử lý LoRa - ưu tiên cao"""
        logger.info("LoRa worker thread started")
        while self.running:
            try:
                # Handle LoRa RX
                self.handle_lora_rx()
                
                # Handle MQTT commands
                self.handle_mqtt_command()
                
                # Process pending commands
                self.send_pending_command()
                
                # Check user confirmations timeout
                self.check_confirmations_timeout()
                
                time.sleep(0.1)  # Small delay to prevent CPU hogging
                
            except Exception as e:
                logger.error(f"LoRa worker error: {e}")
                time.sleep(1)
        
        logger.info("LoRa worker thread stopped")
    
    def ai_worker(self):
        """Luồng xử lý AI - chạy song song"""
        logger.info("AI worker thread started")
        while self.running:
            try:
                now = time.time()
                
                # YOLO classification - daily at 8:00 AM
                if self.should_run_yolo():
                    logger.info("Running daily YOLO plant stage classification...")
                    event = self.ai.classify_plant_stage()
                    if event:
                        self.current_plant_stage = event.class_name
                        yolo_data = {
                            "event": "plant_stage_classification",
                            "stage": event.class_name,
                            "confidence": event.confidence,
                            "image_path": event.image_path
                        }
                        self.mqtt.publish_telemetry(yolo_data)
                        self.last_yolo_run = now
                        logger.info(f"Plant stage updated: {event.class_name}")
                
                # Irrigation decision - every 15 minutes
                if now - self.last_irrigation_check >= 900:  # 15 minutes
                    logger.info("Running irrigation decision analysis...")
                    self.make_irrigation_decision()
                    self.last_irrigation_check = now
                
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"AI worker error: {e}")
                time.sleep(60)
        
        logger.info("AI worker thread stopped")
    
    def parse_node_telemetry(self, payload: str) -> Optional[NodeStatus]:
        """Parse telemetry từ node"""
        try:
            # Format: gate01-node01-PUMP:1-VALVE:0-HUMI1:35.2-TEMP1:25.3-PH1:6.7-HUMI2:38.1-TEMP2:26.0-PH2:6.9-OVERRIDE:0
            parts = payload.split('-')
            
            if len(parts) < 3 or parts[0] != GATEWAY_ID or parts[1] != NODE_ID:
                logger.warning(f"Invalid telemetry format or wrong gateway/node ID: {payload}")
                return None
            
            status = NodeStatus(parts[1])  # node01
            
            # Parse key:value pairs từ phần tử thứ 3 trở đi
            for part in parts[2:]:
                if ':' in part:
                    key, val = part.split(':', 1)
                    
                    if key == "PUMP":
                        status.pump = int(val) == 1
                    elif key == "VALVE":
                        status.valve = int(val) == 1
                    elif key == "HUMI1":
                        status.soil1 = float(val)
                    elif key == "TEMP1":
                        status.temp1 = float(val)
                    elif key == "PH1":
                        status.ph1 = float(val)
                    elif key == "HUMI2":
                        status.soil2 = float(val)
                    elif key == "TEMP2":
                        status.temp2 = float(val)
                    elif key == "PH2":
                        status.ph2 = float(val)
                    elif key == "OVERRIDE":
                        status.override = int(val) == 1
            
            status.last_update = time.time()
            status.rssi = self.lora.last_rssi
            status.snr = self.lora.last_snr
            status.frame_count += 1
            
            logger.info(f"Parsed telemetry: pump={status.pump}, valve={status.valve}, soil1={status.soil1}%, temp1={status.temp1}°C")
            return status
        except Exception as e:
            logger.error(f"Telemetry parsing error: {e}")
            return None
    
    def format_lora_command(self, cmd: PendingCommand) -> str:
        """Format command cho LoRa - khớp với node"""
        if cmd.action == "control_pump":
            pump_val = cmd.params.get("pump", 0)
            return f"{GATEWAY_ID}-{cmd.node_id}-pump-{pump_val}"
        elif cmd.action == "control_valve":
            valve_val = cmd.params.get("valve", 0)
            return f"{GATEWAY_ID}-{cmd.node_id}-valve-{valve_val}"
        elif cmd.action == "control_both":
            # Node không support control_both, chỉ gửi pump command
            pump_val = cmd.params.get("pump", 0)
            return f"{GATEWAY_ID}-{cmd.node_id}-pump-{pump_val}"
        else:
            return f"{GATEWAY_ID}-{cmd.node_id}-debug"
    
    def handle_lora_rx(self):
        """Xử lý nhận LoRa"""
        logger.debug("Gateway: Checking LoRa for incoming data...")
        data = self.lora.receive(timeout=0.1)
        if not data:
            logger.debug("Gateway: No LoRa data received")
            return
        
        logger.info(f"Gateway: LoRa data received: {data}")
        
        # Check nếu là ACK từ node
        if "ACK" in data and NODE_ID in data:
            logger.info(f"Gateway: ACK received from node: {data}")
            # Remove command từ pending list
            if self.pending_commands:
                cmd = self.pending_commands[0]
                logger.info(f"Gateway: Command completed successfully: {cmd.action}")
                self.mqtt.publish_rpc_response(cmd.rpc_id, {"status": "success"})
                self.pending_commands.pop(0)
            else:
                logger.warning("Gateway: Received ACK but no pending command")
            return
        
        # Check nếu là manual override reject
        if "MANUAL_OVERRIDE_ACTIVE" in data and NODE_ID in data:
            logger.warning(f"Gateway: Command rejected - manual override active: {data}")
            # Extract remaining time
            parts = data.split('-')
            remaining_time = 0
            if len(parts) >= 4:
                try:
                    remaining_time = int(parts[3])
                except:
                    pass
            
            if self.pending_commands:
                cmd = self.pending_commands[0]
                logger.warning(f"Gateway: Command failed due to manual override: {cmd.action}")
                self.mqtt.publish_rpc_response(cmd.rpc_id, {
                    "status": "error", 
                    "message": "Manual override active",
                    "remaining_seconds": remaining_time
                })
                self.pending_commands.pop(0)
            return
        
        # Parse telemetry từ node
        if GATEWAY_ID in data and NODE_ID in data and "MANUAL_OVERRIDE_ACTIVE" not in data:
            logger.info(f"Gateway: Parsing telemetry from node: {data}")
            status = self.parse_node_telemetry(data)
            if status:
                self.nodes_status[status.node_id] = status
                logger.info(f"Gateway: Telemetry parsed successfully - pump={status.pump}, valve={status.valve}")
                
                # Publish MQTT
                telemetry = {
                    "node": status.node_id,
                    "pump": status.pump,
                    "valve": status.valve,
                    "soil1": status.soil1,
                    "soil2": status.soil2,
                    "temp1": status.temp1,
                    "temp2": status.temp2,
                    "ph1": status.ph1,
                    "ph2": status.ph2,
                    "override": status.override,
                    "rssi": status.rssi,
                    "snr": status.snr,
                    "frame_count": status.frame_count
                }
                self.mqtt.publish_telemetry(telemetry)
                logger.info("Gateway: Telemetry published to MQTT")
                
                # Update latest telemetry for AI decisions
                self.latest_telemetry = telemetry
                self.node_online = True
                
                # Send ACK back to node
                ack = f"{GATEWAY_ID}-{status.node_id}-ACK"
                logger.info(f"Gateway: Sending ACK to node: {ack}")
                self.lora.send(ack)
                logger.info(f"Gateway: ACK sent to {status.node_id}")
            else:
                logger.error(f"Gateway: Failed to parse telemetry: {data}")
        else:
            logger.warning(f"Gateway: Unknown LoRa data format: {data}")
    
    def handle_mqtt_command(self):
        """Xử lý nhận command từ MQTT"""
        cmd_tuple = self.mqtt.get_command()
        if not cmd_tuple:
            return
        
        payload, rpc_id = cmd_tuple
        try:
            method = payload.get("method", "")
            params = payload.get("params", {})
            
            logger.info(f"RPC command received: method={method}, params={params}")
            
            # Format command
            cmd = None
            if method == "control_pump":
                cmd = PendingCommand(NODE_ID, "control_pump", 
                                   {"pump": params.get("pump", 0)}, rpc_id)
            elif method == "control_both":
                cmd = PendingCommand(NODE_ID, "control_both",
                                   {"pump": params.get("pump", 0),
                                    "valve": params.get("valve", 0),
                                    "duration": params.get("duration", 0)}, rpc_id)
            
            if cmd:
                self.pending_commands.append(cmd)
                logger.info(f"Command queued: {method}")
        except Exception as e:
            logger.error(f"Command parsing error: {e}")
    
    def send_pending_command(self):
        """Gửi command đang chờ"""
        if not self.pending_commands:
            return
        
        cmd = self.pending_commands[0]
        now = time.time()
        
        # Chưa gửi
        if cmd.send_ts is None:
            # Check node alive
            if NODE_ID not in self.nodes_status:
                logger.warning(f"Node {NODE_ID} offline, cannot send command")
                self.mqtt.publish_rpc_response(cmd.rpc_id, 
                    {"status": "error", "message": "Node offline"})
                self.pending_commands.pop(0)
                return
            
            if now - self.nodes_status[NODE_ID].last_update > NODE_TIMEOUT:
                logger.warning(f"Node {NODE_ID} timeout")
                self.mqtt.publish_rpc_response(cmd.rpc_id,
                    {"status": "error", "message": "Node timeout"})
                self.pending_commands.pop(0)
                return
            
            # Send command
            lora_cmd = self.format_lora_command(cmd)
            if self.lora.send(lora_cmd):
                cmd.send_ts = now
                cmd.retry_count = 0
                logger.info(f"Command sent: {lora_cmd}")
            else:
                logger.error("Failed to send command")
        
        # Chờ ACK
        elif now - cmd.send_ts > CMD_ACK_TIMEOUT:
            if cmd.retry_count < CMD_RETRY_MAX:
                cmd.retry_count += 1
                cmd.send_ts = None
                logger.info(f"Command retry: {cmd.retry_count}/{CMD_RETRY_MAX}")
            else:
                logger.error("Command max retries exceeded")
                self.mqtt.publish_rpc_response(cmd.rpc_id,
                    {"status": "error", "message": "No ACK after retries"})
                self.pending_commands.pop(0)
    
    def check_health(self):
        """Health check định kỳ"""
        now = time.time()
        if now - self.last_health_check < HEARTBEAT_CHECK:
            return
        
        self.last_health_check = now
        
        # Check MQTT
        if not self.mqtt.connected:
            logger.warning("MQTT disconnected, attempting reconnect...")
            self.mqtt.connect()
        
        # Check LoRa
        if not self.lora.initialized:
            logger.warning("LoRa not initialized, attempting reset...")
            self.lora.reset()
        
        # Check node timeout
        node_online = False
        for node_id, status in self.nodes_status.items():
            age = now - status.last_update
            if age > NODE_TIMEOUT:
                logger.warning(f"Node {node_id} offline (age: {age}s)")
                self.mqtt.publish_telemetry({
                    "event": "node_offline",
                    "node": node_id,
                    "offline_duration_s": int(age)
                })
            else:
                node_online = True
        
        self.node_online = node_online
    
    def should_run_yolo(self):
        """Kiểm tra có nên chạy YOLO classification không (daily at 8:00 AM)"""
        try:
            now = datetime.now()
            scheduled_hour = 8
            scheduled_min = 0
            
            # Allow 2-minute window
            delta = abs((now.replace(hour=scheduled_hour, minute=scheduled_min, second=0, microsecond=0) - now).total_seconds())
            if delta < 120:  # 2 phút
                if time.time() - self.last_yolo_run > 3600:  # Chỉ 1 lần/giờ
                    return True
        except Exception as e:
            logger.warning(f"YOLOv8 schedule check error: {e}")
        
        return False
    
    def make_irrigation_decision(self):
        """Thực hiện quyết định tưới tiêu dựa trên dữ liệu cảm biến và AI"""
        try:
            # Get latest sensor data
            if not hasattr(self, 'latest_telemetry') or not self.latest_telemetry:
                logger.warning("No telemetry data available for irrigation decision")
                return
            
            # Create irrigation decision
            decision = self.ai.make_irrigation_decision(
                self.latest_telemetry, 
                self.current_plant_stage
            )
            
            if decision.needs_user_confirmation:
                # Send to user for confirmation
                self.pending_confirmations[decision.id] = decision
                self.mqtt.publish_irrigation_request(decision)
                logger.info(f"Irrigation decision {decision.id} sent for user confirmation")
            else:
                # Execute immediately
                self.execute_irrigation_decision(decision)
                
        except Exception as e:
            logger.error(f"Error making irrigation decision: {e}")
    
    def execute_irrigation_decision(self, decision):
        """Thực hiện quyết định tưới tiêu"""
        try:
            # Create command for node
            cmd = {
                "cmd": "IRRIGATE",
                "duration": decision.duration,
                "reason": decision.reason
            }
            
            # Add to pending commands
            self.pending_commands.append(cmd)
            
            # Publish to MQTT
            self.mqtt.publish_irrigation_decision(decision)
            
            logger.info(f"Irrigation decision executed: {decision.duration}s, reason: {decision.reason}")
            
        except Exception as e:
            logger.error(f"Error executing irrigation decision: {e}")
    
    def handle_user_confirmation(self, confirmation):
        """Xử lý xác nhận từ người dùng"""
        try:
            decision_id = confirmation.get("decision_id")
            approved = confirmation.get("approved", False)
            
            if decision_id in self.pending_confirmations:
                decision = self.pending_confirmations.pop(decision_id)
                
                if approved:
                    self.execute_irrigation_decision(decision)
                    logger.info(f"User approved irrigation decision {decision_id}")
                else:
                    logger.info(f"User rejected irrigation decision {decision_id}")
                    
                # Publish confirmation result
                self.mqtt.publish_confirmation_result(decision_id, approved)
            else:
                logger.warning(f"Unknown decision ID: {decision_id}")
                
        except Exception as e:
            logger.error(f"Error handling user confirmation: {e}")
    
    def check_confirmations_timeout(self):
        """Kiểm tra timeout của các confirmation đang chờ"""
        try:
            now = time.time()
            timeout_decisions = []
            
            for decision_id, decision in self.pending_confirmations.items():
                if now - decision.timestamp > 300:  # 5 minutes timeout
                    timeout_decisions.append(decision_id)
            
            for decision_id in timeout_decisions:
                decision = self.pending_confirmations.pop(decision_id)
                logger.warning(f"Confirmation timeout for decision {decision_id}")
                # Optionally execute with default action or notify user
                
        except Exception as e:
            logger.error(f"Error checking confirmations timeout: {e}")
    
    def send_pending_command(self):
        """Gửi lệnh đang chờ tới node"""
        try:
            if self.pending_commands and hasattr(self, 'node_online') and self.node_online:
                cmd = self.pending_commands.pop(0)
                success = self.send_command_to_node(cmd)
                if not success:
                    # Put back to queue if failed
                    self.pending_commands.insert(0, cmd)
                    
        except Exception as e:
            logger.error(f"Error sending pending command: {e}")
    
    def send_command_to_node(self, cmd):
        """Gửi lệnh tới node qua LoRa"""
        try:
            # Format command for LoRa transmission
            cmd_data = json.dumps(cmd).encode('utf-8')
            
            # Send via LoRa
            self.lora.send(cmd_data)
            
            # Wait for ACK (implement timeout)
            ack_received = False
            start_time = time.time()
            
            while time.time() - start_time < 5:  # 5 second timeout
                if self.lora.receive():
                    ack_received = True
                    break
                time.sleep(0.1)
            
            if ack_received:
                logger.info(f"Command sent successfully: {cmd}")
                return True
            else:
                logger.warning(f"Command send timeout: {cmd}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending command to node: {e}")
            return False
    
    def run(self):
        """Main loop với threading"""
        if not self.start():
            return
        
        logger.info("Starting gateway threads...")
        
        # Start LoRa thread (high priority)
        self.lora_thread = threading.Thread(target=self.lora_worker, name="LoRaWorker")
        self.lora_thread.daemon = True
        self.lora_thread.start()
        
        # Start AI thread
        self.ai_thread = threading.Thread(target=self.ai_worker, name="AIWorker")
        self.ai_thread.daemon = True
        self.ai_thread.start()
        
        logger.info("Gateway threads started successfully")
        
        try:
            # Main thread monitors health and handles shutdown
            while self.running:
                self.check_health()
                time.sleep(10)  # Health check every 10 seconds
                
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Unexpected error in main thread: {e}")
        finally:
            self.stop()

# ============================================================================
# MAIN
# ============================================================================

def lora_thread():
    """Luồng xử lý LoRa"""
    logger.info("LoRa thread started")
    while True:
        try:
            # Handle LoRa RX
            gateway.handle_lora_rx()
            
            # Handle MQTT commands
            gateway.handle_mqtt_command()
            
            # Process pending commands
            gateway.send_pending_command()
            
            # Check user confirmations timeout
            gateway.check_confirmations_timeout()
            
            time.sleep(0.1)
        except Exception as e:
            logger.error(f"LoRa thread error: {e}")
            time.sleep(1)

def scheduler_thread():
    """Luồng xử lý AI và scheduling"""
    logger.info("Scheduler thread started")
    while True:
        try:
            now = time.time()
            
            # YOLO classification - daily at 8:00 AM
            if gateway.should_run_yolo():
                logger.info("Running daily YOLO plant stage classification...")
                event = gateway.ai.classify_plant_stage()
                if event:
                    gateway.current_plant_stage = event.class_name
                    yolo_data = {
                        "event": "plant_stage_classification",
                        "stage": event.class_name,
                        "confidence": event.confidence,
                        "image_path": event.image_path
                    }
                    gateway.mqtt.publish_telemetry(yolo_data)
                    gateway.last_yolo_run = now
                    logger.info(f"Plant stage updated: {event.class_name}")
            
            # Irrigation decision - every 15 minutes
            if now - gateway.last_irrigation_check >= 900:  # 15 minutes
                logger.info("Running irrigation decision analysis...")
                gateway.make_irrigation_decision()
                gateway.last_irrigation_check = now
            
            # Health check
            gateway.check_health()
            
            time.sleep(60)  # Check every minute
            
        except Exception as e:
            logger.error(f"Scheduler thread error: {e}")
            time.sleep(60)

# Global gateway instance
gateway = None

def main():
    global gateway
    gateway = IrrigationGateway()
    
    if not gateway.start():
        logger.error("Failed to start gateway")
        return
    
    logger.info("Gateway Pi 4 Hybrid AI is running...")
    
    # Start threads
    t1 = threading.Thread(target=lora_thread, daemon=True)
    t2 = threading.Thread(target=scheduler_thread, daemon=True)
    t1.start()
    t2.start()
    
    print("Gateway Pi 4 Hybrid AI is running...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        gateway.stop()

if __name__ == "__main__":
    main()
