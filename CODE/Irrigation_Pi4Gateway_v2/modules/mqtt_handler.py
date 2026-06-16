# ============================================================================
# MQTT HANDLER
# ============================================================================

import json
import time
import queue
import requests
from typing import Optional
from .data_structures import NodeStatus, PendingCommand, IrrigationDecision

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("Paho MQTT not available")

from .config import MQTT_BROKER, MQTT_PORT, MQTT_USER, MQTT_PASS, MQTT_TIMEOUT
from .logger import logger

class MQTTHandler:
    def __init__(self, broker=None, port=None, user=None, password=None):
        self.broker = broker or MQTT_BROKER
        self.port = port or MQTT_PORT
        self.user = user or MQTT_USER
        self.password = password or MQTT_PASS

        self.client = mqtt.Client(client_id="gateway_pi4")
        self.connected = False
        self.command_queue = queue.Queue()
        self.rpc_callbacks = {}

        # Callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

        self.ignore_next_rollback = False 

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

    def get_jwt_token(self):
        """
        Đăng nhập vào ThingsBoard để lấy JWT Token
        """
        url = "https://thingsboard.cloud/api/auth/login"
        credentials = {
            "username": "caolephungcp@gmail.com",
            "password": "Songngu2702."
        }
        
        try:
            response = requests.post(url, json=credentials)
            if response.status_code == 200:
                token_data = response.json()
                # Lưu token để dùng cho các yêu cầu sau
                self.jwt_token = token_data.get("token")
                return self.jwt_token
            else:
                print(f"Đăng nhập thất bại: {response.status_code}")
        except Exception as e:
            print(f"Lỗi khi lấy JWT Token: {e}")
        return None

    def _on_message(self, client, userdata, msg):
        """Callback khi nhận message"""
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode('utf-8'))
            logger.debug(f"MQTT message: {topic} -> {payload}")

            # Xử lý Shared Attributes (Lệnh điều khiển mới)
            if "attributes" in topic:
                if self.ignore_next_rollback:
                    logger.info("Ignoring attribute update caused by own rollback.")
                    self.ignore_next_rollback = False # Tắt cờ để nhận các lệnh tiếp theo từ User
                    return
                # ThingsBoard gửi shared attributes trực tiếp trong payload hoặc trong key 'shared'
                data = payload.get("shared", payload) 
                logger.info(f"Shared Attributes received: {data}")
                
                # Đưa vào queue để xử lý tuần tự. 
                # Với Attribute, chúng ta không có rpc_id nên để None.
                self.command_queue.put((data, None))

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
    
    def publish_shared_attributes(self, data):
        # deviceId lấy từ thông tin thiết bị của bạn
        device_id = "657b4290-2426-11f1-afd7-eb430bfb427f"
        url = f"https://thingsboard.cloud/api/plugins/telemetry/DEVICE/{device_id}/attributes/SHARED_SCOPE"
        
        # Bạn cần lấy JWT Token của tài khoản (không phải Access Token của thiết bị)
        # Hoặc nếu Gateway có quyền Admin, hãy dùng Token đó.
        headers = {
            "X-Authorization": f"Bearer {self.get_jwt_token()}", 
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(url, headers=headers, data=json.dumps(data))
            return response.status_code == 200
        except Exception as e:
            print(f"Lỗi gửi Shared Attribute qua HTTP: {e}")
            return False

    def get_command(self) -> Optional[tuple]:
        """Lấy command từ queue"""
        try:
            return self.command_queue.get_nowait()
        except:
            return None

    def publish_irrigation_decision(self, decision) -> bool:
        """Gửi quyết định tưới tiêu đã thực hiện"""
        try:
            payload = json.dumps({
                "event": "irrigation_decision",
                "decision": decision.decision,
                "confidence": decision.confidence,
                "reason": decision.reason,
                "executed": True
            })
            self.client.publish("v1/devices/me/irrigation/decision", payload)
            logger.info(f"Irrigation decision published: {decision.decision}")
            return True
        except Exception as e:
            logger.error(f"Irrigation decision publish failed: {e}")
            return False