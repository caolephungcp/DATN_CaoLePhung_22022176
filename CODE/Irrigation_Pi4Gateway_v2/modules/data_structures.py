# ============================================================================
# DATA STRUCTURES
# ============================================================================

import time
from typing import Dict, List, Optional

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
        self.last_update = 0
        self.rssi = 0
        self.snr = 0
        self.frame_count = 0

class PendingCommand:
    def __init__(self, node_id, action, params, rpc_id=None):
        self.node_id = node_id
        self.action = action  
        self.params = params  
        self.rpc_id = rpc_id
        self.ts = time.time()
        self.send_ts = None
        self.retry_count = 0
        self.sent_data = None

class YOLOEvent:
    def __init__(self, class_name, confidence, image_path=None):
        self.timestamp = time.time()
        self.class_name = class_name 
        self.confidence = confidence
        self.image_path = image_path

class IrrigationDecision:
    """Quyết định tưới nước"""
    IRRIGATE = "irrigate"  
    NO_IRRIGATE = "no_irrigate"  

class IrrigationEvent:
    def __init__(self, decision: str, confidence: float, reason: str, sensor_data: dict = None):
        self.timestamp = time.time()
        self.decision = decision
        self.confidence = confidence
        self.reason = reason
        self.sensor_data = sensor_data or {}
