# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

import time
import threading
from datetime import datetime

from .logger import logger
from .irrigation_gateway import IrrigationGateway

# Global gateway instance
gateway = None

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

            time.sleep(0.1)
        except Exception as e:
            logger.error(f"LoRa thread error: {e}")
            time.sleep(1)

def scheduler_thread():
    """Luồng xử lý AI và lập lịch tưới nước"""
    logger.info("Scheduler thread started")
    
    # Khởi tạo mốc thời gian kiểm tra tưới lần đầu tiên
    last_irrigation_check = time.time()
    
    while True:
        try:
            now_ts = time.time()
            now_dt = datetime.now()  # Lấy thời gian thực từ hệ thống

            # 1. Gọi trực tiếp hàm nhận diện giai đoạn cây trồng
            # Hàm này đã tự kiểm tra, nếu không phải 8h hoặc 16h sẽ tự động trả về 0
            stage_code = gateway.ai.classify_plant_stage(now_dt)
            
            # Nếu trả về từ 1-5 (trúng khung giờ và nhận diện thành công)
            if stage_code > 0:
                gateway.at = stage_code
                
                gateway.mqtt.publish_shared_attributes({"AT1": stage_code})  # Cập nhật giai đoạn cây mới lên ThingsBoard

                logger.info(f"Đã cập nhật giai đoạn cây mới: {stage_code}")

            # 2. Quyết định tưới nước - Tự động chạy chu kỳ mỗi 15 phút (900 giây)
            if now_ts - last_irrigation_check >= 30:
                logger.info("Đang chạy phân tích để đưa ra quyết định tưới...")

                status = gateway.nodes_status["node01"]
                
                data = {
                    "temp": status.temp1,
                    "soil": status.soil1,
                    "ph": status.ph1,
                    "weather_temp": gateway.weather_data["weather_temp"],
                    "weather_humidity": gateway.weather_data["weather_humidity"],
                    "weather_pop": gateway.weather_data["weather_pop"],
                    "weather_rain_3h": gateway.weather_data["weather_rain_3h"]
                } 
                
                # Gọi trực tiếp hàm quyết định tưới 
                # Tham số 'auto' truyền True/False tùy thuộc cấu hình hệ thống của bạn
                irrigation_result = gateway.ai.make_irrigation_decision(
                    data=data,
                    plant_stage=gateway.at,
                    auto=gateway.auto
                )
                
                # Thực hiện hành động bật/tắt bơm dựa trên kết quả trả về (1 hoặc 0)
                if irrigation_result == 1:
                    gateway.mqtt.publish_shared_attributes({"F1_P1": True})
                elif irrigation_result == 0:                  
                    gateway.mqtt.publish_shared_attributes({"F1_P1": False})

                last_irrigation_check = now_ts

            # Ngủ 60 giây trước khi bước vào chu kỳ kiểm tra tiếp theo
            time.sleep(60)

        except Exception as e:
            logger.error(f"Lỗi trong luồng Scheduler: {e}")
            time.sleep(60)

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