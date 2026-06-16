# ============================================================================
# IRRIGATION GATEWAY
# ============================================================================

import time
import json
import threading
from datetime import datetime
from tokenize import String
from typing import Dict, List, Optional

from .config import GATEWAY_ID, NODE_ID, NODE_TIMEOUT, HEARTBEAT_CHECK, CMD_ACK_TIMEOUT, CMD_RETRY_MAX
from .logger import logger
from .data_structures import NodeStatus, PendingCommand, IrrigationDecision
from .lora_handler import LoRaHandler
from .mqtt_handler import MQTTHandler
from .ai_handler import AIHandler

class IrrigationGateway:
    def __init__(self):
        self.lora = LoRaHandler()
        self.mqtt = MQTTHandler()
        self.ai = AIHandler()

        self.nodes_status: Dict[str, NodeStatus] = {}
        self.pending_command: Optional[PendingCommand] = None

        # Threading
        self.lora_thread = None
        self.ai_thread = None
        self.running = False

        # Timers
        self.last_health_check = 0
        self.last_yolo_run = 0
        self.last_irrigation_check = 0

        self.at = 0 
        self.auto = False

        self.mqtt_connected = False
        self.latest_telemetry = None
        self.node_online = False

        self.weather_data = {
            "weather_temp": 0.0,
            "weather_humidity": 0,
            "weather_pop": 0,
            "weather_rain_3h": 0.0
        }

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
        logger.info("Gateway stopped")

    def parse_node_telemetry(self, payload: str) -> Optional[NodeStatus]:
        """Parse telemetry từ node"""
        try:
            # Format: gate01-node01-PUMP:1-VALVE:0-HUMI1:35.2-TEMP1:25.3-PH1:6.7-HUMI2:38.1-TEMP2:26.0-PH2:6.9
            parts = payload.split('-')

            if len(parts) < 3 or parts[0] != GATEWAY_ID or parts[1] != NODE_ID:
                logger.warning(f"Invalid telemetry format or wrong gateway/node ID: {payload}")
                return None

            status = NodeStatus(parts[1])  # node01

            # Parse key:value
            for part in parts[2:]:
                if ':' in part:
                    key, val = part.split(':', 1)

                    if key == "F1_P1":
                        status.pump = int(val) == 1
                    elif key == "F1_P2":
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

            status.last_update = time.time()
            status.rssi = self.lora.last_rssi
            status.snr = self.lora.last_snr
            status.frame_count += 1

            logger.info(f"Parsed telemetry: F1_P1={status.pump}, F1_P2={status.valve}, soil1={status.soil1}%, temp1={status.temp1}°C")
            return status
        except Exception as e:
            logger.error(f"Telemetry parsing error: {e}")
            return None

    def format_lora_command(self, cmd: PendingCommand) -> str:
        """Format command cho LoRa"""
        if cmd.action == "F1_P1":
            pump_val = cmd.params.get("F1_P1", 0)
            return f"{GATEWAY_ID}-{cmd.node_id}-F1_P1-{pump_val}"
        elif cmd.action == "F1_P2":
            valve_val = cmd.params.get("F1_P2", 0)
            return f"{GATEWAY_ID}-{cmd.node_id}-F1_P2-{valve_val}"
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


        if GATEWAY_ID in data:
            # Parse telemetry từ node
            if "ACK" not in data and "F1_P1" in data:
                logger.info(f"Gateway: Parsing telemetry from node: {data}")
                status = self.parse_node_telemetry(data)
                
                if status:
                    self.nodes_status[status.node_id] = status
                    print(f"Giá trị của node_id: {status.node_id} | Kiểu dữ liệu thực tế: {type(status.node_id)}")
                    logger.info(f"Gateway: Telemetry parsed successfully - F1_P1={status.pump}, F1_P2={status.valve}")

                    # Publish MQTT
                    telemetry = {
                        "node": status.node_id,
                        "F1_P1": status.pump,
                        "F1_P2": status.valve,
                        "soil1": status.soil1,
                        "soil2": status.soil2,
                        "temp1": status.temp1,
                        "temp2": status.temp2,
                        "ph1": status.ph1,
                        "ph2": status.ph2,
                        "rssi": status.rssi,
                        "snr": status.snr,
                        "frame_count": status.frame_count
                    }
                    self.mqtt.publish_telemetry(telemetry)
                    logger.info("Gateway: Telemetry published to MQTT")

                    self.mqtt.ignore_next_rollback  = True
                    prefix = f"F{status.node_id[-1]}"
                    shared_update = {
                        f"{prefix}_P1": status.pump,
                        f"{prefix}_P2": status.valve
                    }
                    self.mqtt.publish_shared_attributes(shared_update)

                    # Update latest telemetry for AI decisions
                    self.latest_telemetry = telemetry
                    self.node_online = True

                    # Send ACK back to node
                    ack = f"{GATEWAY_ID}-{status.node_id}-ACK"
                    logger.info(f"Gateway: Sending ACK to node: {ack}")
                    self.lora.send(ack)
                    logger.info(f"Tree state {status.node_id}: {self.at}")
                    logger.info(f"Mode auto {status.node_id}: {self.auto}")
                else:
                    logger.error(f"Gateway: Failed to parse telemetry: {data}")

            # Check ACK
            if "ACK" in data:
                logger.info(f"Gateway: ACK received from node {NODE_ID}: {data}")
                if "F1_P1" in data:
                    logger.info(f"Gateway: Command completed successfully: {self.pending_command.action}")
                    self.mqtt.publish_rpc_response(self.pending_command.rpc_id, {"status": not self.nodes_status.get(NODE_ID).pump})
                    self.pending_command = None
                if "F1_P2" in data:
                    logger.info(f"Gateway: Command completed successfully: {self.pending_command.action}")
                    self.mqtt.publish_rpc_response(self.pending_command.rpc_id, {"status": not self.nodes_status.get(NODE_ID).valve})
                    self.pending_command = None
                return
            else:
                logger.warning(f"Gateway: ")

    def handle_mqtt_command(self):
        """Xử lý nhận command từ Shared Attributes"""
        try:
            while True:
                cmd_tuple = self.mqtt.get_command()
                if not cmd_tuple:
                    break

                data, _ = cmd_tuple 
                
                for key in data:
                    val = data[key]
                    
                    # Xử lý điều khiển máy bơm (F1_P1, F1_P2, F2_P1)
                    if key in ["F1_P1", "F1_P2", "F2_P1"]:
                        pump_val = 1 if val is True or val == 1 else 0
                        
                        target_node = "node01" if key.startswith("F1") else "node02"
                        
                        self.pending_command = PendingCommand(
                            target_node, 
                            key,
                            {key: pump_val}, 
                            None 
                        )
                        logger.info(f"New Pump Command: {key} -> {pump_val}")

                    # Xử lý trạng thái cây (AT1, AT2)
                    elif key in ["AT1", "AT2"]:
                        self.at = val
                        logger.info(f"Tree state updated: at = {val}")

                    # Xử lý chế độ (F1, F2)
                    elif key in ["F1"]:
                        self.auto = val
                        logger.info(f"Mode auto updated: {val}")

                    elif key in ["weather_pop", "weather_rain_3h", "weather_temp", "weather_humidity"]:
                        self.weather_data[key] = val
                        logger.info(f"Weather data updated: {key} = {val}")

        except Exception as e:
            logger.error(f"Command parsing error: {e}")

    def send_pending_command(self):
        """Gửi command đang chờ qua LoRa"""
        if not self.pending_command:
            return

        cmd = self.pending_command
        now = time.time()

        if cmd.send_ts is None:
            lora_cmd = self.format_lora_command(cmd)
            if self.lora.send(lora_cmd):
                cmd.send_ts = now
                logger.info(f"LoRa Sent: {lora_cmd}")
            else:
                logger.error("LoRa Hardware Error")
                return

        # Chờ ACK từ Node LoRa
        elif now - cmd.send_ts > CMD_ACK_TIMEOUT:
            if cmd.retry_count < CMD_RETRY_MAX:
                cmd.retry_count += 1
                cmd.send_ts = None # Để vòng lặp sau gửi lại
                logger.info(f"Retry {cmd.retry_count}/{CMD_RETRY_MAX}")
            else:
                # THẤT BẠI HOÀN TOÀN
                cmd.retry_count = 0
                logger.error(f"Command {cmd.action} failed after {CMD_RETRY_MAX} retries")
                
                # ROLLBACK TRÊN SERVER: Cập nhật lại giá trị để App đồng bộ
                for key, val in cmd.params.items():
                    rollback_val = not val
                    self.mqtt.publish_telemetry({f"{key}_error": "timeout"})
                    self.mqtt.ignore_next_rollback  = True
                    self.mqtt.publish_shared_attributes({key: rollback_val})

                    self.pending_command = None  
                
                return
                
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
            while self.running:
                self.check_health()
                time.sleep(10)  

        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Unexpected error in main thread: {e}")
        finally:
            self.stop()

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

                time.sleep(0.1) 

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

                # Irrigation decision
                if now - self.last_irrigation_check >= 900:  # 15 minutes
                    logger.info("Running irrigation decision analysis...")
                    self.make_irrigation_decision(self.auto)
                    self.last_irrigation_check = now

                time.sleep(60)  

            except Exception as e:
                logger.error(f"AI worker error: {e}")
                time.sleep(60)

        logger.info("AI worker thread stopped")