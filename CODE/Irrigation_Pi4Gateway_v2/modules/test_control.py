import time
import json
import logging
from mqtt_handler import MQTTHandler # Đảm bảo file mqtt_handler.py nằm cùng thư mục

# Cấu hình log để thấy dữ liệu in ra
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def main():
    # 1. Khởi tạo và kết nối
    mqtt = MQTTHandler()
    if not mqtt.connect():
        print("Không thể kết nối MQTT!")
        return

    print("--- Đang chờ lệnh từ ThingsBoard (Nhấn Ctrl+C để dừng) ---")

    try:
        while True:
            # 2. Lấy lệnh từ queue (hàm bạn đã viết)
            cmd_tuple = mqtt.get_command()
            
            if cmd_tuple:
                payload, rpc_id = cmd_tuple
                method = payload.get("method")
                params = payload.get("params")

                print(f"\n[NHẬN LỆNH]")
                print(f"- Method: {method}")
                print(f"- Params: {params}")
                print(f"- RPC ID: {rpc_id}")

                # 3. Phản hồi ngay lập tức để nút nhấn trên TB không bị xoay vòng (Loading)
                # Bạn trả về bất cứ thứ gì, miễn là có phản hồi
                mqtt.publish_rpc_response(rpc_id, {"result": "success", "echo_params": params})
                print("-> Đã phản hồi server.")

            time.sleep(0.1) # Tránh tốn CPU
    except KeyboardInterrupt:
        mqtt.disconnect()
        print("\nĐã dừng test.")

if __name__ == "__main__":
    main()