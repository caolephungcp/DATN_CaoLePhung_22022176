import time
import os
import subprocess
from datetime import datetime
from typing import Optional
import numpy as np

try:
    import cv2
    import onnxruntime as ort
except ImportError:
    print("OpenCV or ONNX Runtime not available")

from .config import YOLO_MODEL_PATH, IMAGE_SAVE_PATH
from .data_structures import YOLOEvent, IrrigationEvent, IrrigationDecision
from .logger import logger

class AIHandler:
    def __init__(self, yolo_model_path=None, irrigation_model_path=None):
        self.yolo_model_path = yolo_model_path or YOLO_MODEL_PATH
        self.irrigation_model = None  # Placeholder for future irrigation model
        self.session = None
        self.initialized = False
        self.threshold_off = 80.0
        self.threshold_on = 50.0

        try:
            logger.info(f"Loading YOLOv8 ONNX model: {self.yolo_model_path}")
            self.session = ort.InferenceSession(self.yolo_model_path, providers=['CPUExecutionProvider'])

            self.initialized = True
            logger.info("AI Handler initialized successfully with ONNX Runtime")
        except Exception as e:
            logger.error(f"AI Handler initialization failed: {e}")

    def capture_image(self) -> Optional[str]:
        """Chụp ảnh từ Pi Camera"""
        try:
            # Tạo thư mục lưu trữ nếu chưa có
            os.makedirs(IMAGE_SAVE_PATH, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_path = f"{IMAGE_SAVE_PATH}/capture_{timestamp}.jpg"

            logger.info("Capturing image via rpicam-jpeg...")
            subprocess.run(["rpicam-jpeg", "-o", image_path, "--nopreview", "-t", "1000"], check=True)
            
            logger.info(f"Image captured successfully: {image_path}")
            return image_path
        except Exception as e:
            logger.error(f"Image capture via rpicam-jpeg failed: {e}")
            return None

    def classify_plant_stage(self, current_time: datetime) -> int:
        """
        Phân loại giai đoạn cây trồng dựa trên mô hình ONNX 320x320.
        Chỉ thực hiện chạy mô hình vào lúc 8h sáng hoặc 16h chiều.
        Trả về: 1, 2, 3, 4, 5 tương ứng với giai đoạn cây; trả về 0 nếu ngoài giờ hoặc lỗi.
        """
        if False:
            logger.info(f"Không phải khung giờ nhận diện ({current_time.strftime('%H:%M')}). Bỏ qua.")
            return 0

        if not self.initialized or not self.session:
            logger.error("YOLO ONNX model not available")
            return 0

        try:
            image_path = self.capture_image()
            if not image_path:
                return 0

            img = cv2.imread(image_path)
            if img is None:
                logger.error("Failed to read captured image via OpenCV")
                return 0
                
            img_h, img_w, _ = img.shape

            input_img = cv2.resize(img, (320, 320))
            input_img = input_img.astype(np.float32) / 255.0  # Chuẩn hóa pixel về khoảng [0, 1]
            input_img = np.transpose(input_img, (2, 0, 1))    # Chuyển đổi định dạng từ HWC sang CHW
            input_img = np.expand_dims(input_img, axis=0)     # Thêm chiều Batch size (1, 3, 320, 320)

            logger.info("Running YOLOv8 ONNX plant stage classification...")
            input_name = self.session.get_inputs()[0].name
            outputs = self.session.run(None, {input_name: input_img})

            # trích xuất kết quả nhận diện
            predictions = np.squeeze(outputs[0]) 
            predictions = np.transpose(predictions, (1, 0)) 

            CONF_THRESHOLD = 0.25
            IOU_THRESHOLD = 0.45
            
            stage_values = [1, 2, 3, 4, 5]

            boxes = []
            confidences = []
            class_ids = []

            x_factor = img_w / 320
            y_factor = img_h / 320

            for pred in predictions:
                scores = pred[4:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                
                if confidence > CONF_THRESHOLD:
                    xc, yc, w, h = pred[0], pred[1], pred[2], pred[3]
                    
                    xmin = int((xc - w / 2) * x_factor)
                    ymin = int((yc - h / 2) * y_factor)
                    box_w = int(w * x_factor)
                    box_h = int(h * y_factor)
                    
                    boxes.append([xmin, ymin, box_w, box_h])
                    confidences.append(float(confidence))
                    class_ids.append(class_id)

            # Áp dụng NMS lọc bỏ các khung trùng lắp
            indices = cv2.dnn.NMSBoxes(boxes, confidences, CONF_THRESHOLD, IOU_THRESHOLD)

            if len(indices) > 0:
                # Lấy phần tử nhận diện có độ tự tin cao nhất đầu tiên làm kết quả chính
                best_idx = indices.flatten()[0]
                class_id = class_ids[best_idx]
                confidence = confidences[best_idx]
                
                plant_stage = stage_values[class_id] if class_id < len(stage_values) else 0
                
                logger.info(f"Plant stage classified: {plant_stage} (confidence: {confidence:.2f})")
                return plant_stage
            else:
                logger.warning("No plant stages detected with confidence above threshold")

        except Exception as e:
            logger.error(f"YOLO ONNX inference failed: {e}")

        return 0

    def make_irrigation_decision(self, data: dict, plant_stage: str = None, auto: bool = False) -> Optional[int]:
        """
        Quyết định tưới nước dựa trên dữ liệu cảm biến thực địa, dự báo thời tiết và giai đoạn sinh trưởng của ngô.
        Trả về: 1 nếu cần bật tưới, 0 nếu không cần tưới hoặc cần tắt tưới.
        """
        if auto:
            try:
                temp = data.get("temp", 0)       
                soil = data.get("soil", 0)        
                ph = data.get("ph", 0)            
                weather_temp = data.get("weather_temp", 0)       
                weather_humidity = data.get("weather_humidity", 0) 
                weather_pop = data.get("weather_pop", 0)          
                weather_rain_3h = data.get("weather_rain_3h", 0)  

                try:
                    stage = int(plant_stage)
                except (ValueError, TypeError):
                    stage = 0

                decision = 0

                # Thiết lập cặp ngưỡng threshold_on và threshold_off
                if weather_pop >= 60.0: 
                    if weather_rain_3h > 18.0:
                        logger.info(f"Irrigation decision: {decision} | Stage: {plant_stage}")       
                        return decision
                    elif 10.0 <= weather_rain_3h <= 18.0:
                        if stage in [1, 2]:
                            self.threshold_on = 60.0
                            self.threshold_off = 65.0 # tưới = 1/2
                            stage_desc = "Cây con 2-4 lá"
                        elif stage == 3:
                            self.threshold_on = 60.0
                            self.threshold_off = 70.0 # tưới = 1/2
                            stage_desc = "Phát triển 5-7 lá"
                        elif stage == 4:
                            self.threshold_on = 70.0
                            self.threshold_off = 75.0 # tưới = 1/2
                            stage_desc = "Trưởng thành (7 lá đến trỗ cờ)"
                        elif stage == 5:
                            self.threshold_on = 70.0
                            self.threshold_off = 80.0 # tưới = 1/2
                            stage_desc = "Sau trỗ cờ (Phun râu - Phát triển hạt)"
                        else:
                            # Ngưỡng an toàn mặc định khi hệ thống gặp lỗi nhận diện giai đoạn
                            self.threshold_on = 60.0
                            self.threshold_off = 70.0
                            stage_desc = "Không xác định"
                    else:
                        if stage in [1, 2]:
                            self.threshold_on = 60.0
                            self.threshold_off = 65.0
                            stage_desc = "Cây con 2-4 lá"
                        elif stage == 3:
                            self.threshold_on = 60.0
                            self.threshold_off = 70.0
                            stage_desc = "Phát triển 5-7 lá"
                        elif stage == 4:
                            self.threshold_on = 70.0
                            self.threshold_off = 75.0
                            stage_desc = "Trưởng thành (7 lá đến trỗ cờ)"
                        elif stage == 5:
                            self.threshold_on = 70.0
                            self.threshold_off = 80.0
                            stage_desc = "Sau trỗ cờ (Phun râu - Phát triển hạt)"
                        else:
                            # Ngưỡng an toàn mặc định khi hệ thống gặp lỗi nhận diện giai đoạn
                            self.threshold_on = 60.0
                            self.threshold_off = 70.0
                            stage_desc = "Không xác định"
                else:
                    if stage in [1, 2]:
                        self.threshold_on = 60.0
                        self.threshold_off = 65.0
                        stage_desc = "Cây con 2-4 lá"
                    elif stage == 3:
                        self.threshold_on = 60.0
                        self.threshold_off = 70.0
                        stage_desc = "Phát triển 5-7 lá"
                    elif stage == 4:
                        self.threshold_on = 70.0
                        self.threshold_off = 75.0
                        stage_desc = "Trưởng thành (7 lá đến trỗ cờ)"
                    elif stage == 5:
                        self.threshold_on = 70.0
                        self.threshold_off = 80.0
                        stage_desc = "Sau trỗ cờ (Phun râu - Phát triển hạt)"
                    else:
                        # Ngưỡng an toàn mặc định khi hệ thống gặp lỗi nhận diện giai đoạn
                        self.threshold_on = 60.0
                        self.threshold_off = 70.0
                        stage_desc = "Không xác định"

                if soil < self.threshold_on:
                    decision = 1
                elif self.threshold_on <= soil < self.threshold_off:
                    decision = None
                else:
                    decision = 0
                    
                logger.info(f"Irrigation decision: {decision} | Stage: {plant_stage}")
                return decision

            except Exception as e:
                logger.error(f"Irrigation decision failed: {e}")
                return None
        else:
            logger.info("Auto irrigation disabled, skipping decision")
            return None