import subprocess
import cv2
import numpy as np
import onnxruntime as ort

# ==========================================
# CẤU HÌNH THÔNG SỐ
# ==========================================
IMAGE_PATH = "captured_frame.jpg"
OUTPUT_PATH = "result.jpg"
MODEL_PATH = "best.onnx"

# Định nghĩa các giai đoạn cây ngô của bạn (Sửa lại cho đúng thứ tự khi train)
CLASSES = ["Giai_doan_1", "Giai_doan_2", "Giai_doan_3", "Giai_doan_4", "Giai_doan_5"] 

CONF_THRESHOLD = 0.25  # Độ tự tin tối thiểu để công nhận vật thể
IOU_THRESHOLD = 0.45   # Ngưỡng loại bỏ các khung trùng lặp (NMS)

# ==========================================
# 1. CHỤP ẢNH TỪ PI CAMERA
# ==========================================
print("Chụp ảnh từ Pi Camera...")
subprocess.run(["rpicam-jpeg", "-o", IMAGE_PATH, "--nopreview", "-t", "1000"], check=True)

# ==========================================
# 2. KHỞI TẠO MÔ HÌNH ONNX
# ==========================================
print("Đang tải mô hình ONNX...")
session = ort.InferenceSession(MODEL_PATH, providers=['CPUExecutionProvider'])

# ==========================================
# 3. ĐỌC VÀ TIỀN XỬ LÝ ẢNH
# ==========================================
img = cv2.imread(IMAGE_PATH)
img_h, img_w, _ = img.shape

# Resize về 320x320 theo đúng yêu cầu của mô hình
input_img = cv2.resize(img, (320, 320))
input_img = input_img.astype(np.float32) / 255.0  # Chuẩn hóa về [0, 1]
input_img = np.transpose(input_img, (2, 0, 1))    # Chuyển từ HWC sang CHW
input_img = np.expand_dims(input_img, axis=0)     # Thêm chiều batch (1, 3, 320, 320)

# ==========================================
# 4. CHẠY NHẬN DIỆN (INFERENCE)
# ==========================================
input_name = session.get_inputs()[0].name
outputs = session.run(None, {input_name: input_img})

# ==========================================
# 5. HẬU XỬ LÝ KẾT QUẢ (POST-PROCESSING)
# ==========================================
# Đầu ra của YOLOv8 dạng ONNX thường có cấu trúc: [1, 4 + số_lượng_class, 2100]
predictions = np.squeeze(outputs[0]) 

# Chuyển vị ma trận để dễ xử lý dòng lệnh thành: [2100, 4 + số_lượng_class]
predictions = np.transpose(predictions, (1, 0))

boxes = []
confidences = []
class_ids = []

# Tỷ lệ scale để chuyển tọa độ từ bouding box 320x320 về ảnh gốc
x_factor = img_w / 320
y_factor = img_h / 320

for pred in predictions:
    # Trích xuất điểm số của các class (từ phần tử thứ 4 trở đi)
    scores = pred[4:]
    class_id = np.argmax(scores)
    confidence = scores[class_id]
    
    # Lọc các kết quả có độ tự tin cao hơn ngưỡng
    if confidence > CONF_THRESHOLD:
        # YOLOv8 trả về dạng: [x_center, y_center, width, height]
        xc, yc, w, h = pred[0], pred[1], pred[2], pred[3]
        
        # Chuyển đổi sang dạng tọa độ góc: [x_min, y_min, width, height] để đưa vào OpenCV
        xmin = int((xc - w / 2) * x_factor)
        ymin = int((yc - h / 2) * y_factor)
        box_w = int(w * x_factor)
        box_h = int(h * y_factor)
        
        boxes.append([xmin, ymin, box_w, box_h])
        confidences.append(float(confidence))
        class_ids.append(class_id)

# Áp dụng Non-Maximum Suppression (NMS) để loại bỏ các khung đè lên nhau
indices = cv2.dnn.NMSBoxes(boxes, confidences, CONF_THRESHOLD, IOU_THRESHOLD)

# ==========================================
# 6. HIỂN THỊ KẾT QUẢ VÀ LƯU ẢNH
# ==========================================
print("\n--- KẾT QUẢ NHẬN DIỆN ---")
if len(indices) > 0:
    for i in indices.flatten():
        xmin, ymin, box_w, box_h = boxes[i]
        confidence = confidences[i]
        class_id = class_ids[i]
        class_name = CLASSES[class_id] if class_id < len(CLASSES) else f"Class_{class_id}"
        
        # In kết quả trực tiếp ra Terminal để bạn theo dõi
        print(f"Phát hiện: {class_name} | Độ tự tin: {confidence*100:.2f}% | Toạ độ: [{xmin}, {ymin}, {box_w}, {box_h}]")
        
        # Vẽ khung (Bounding Box) lên ảnh
        cv2.rectangle(img, (xmin, ymin), (xmin + box_w, ymin + box_h), (0, 255, 0), 2)
        
        # Vẽ nhãn tên giai đoạn lên trên khung
        label = f"{class_name}: {confidence*100:.1f}%"
        cv2.putText(img, label, (xmin, ymin - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    
    # Lưu ảnh kết quả đã được vẽ khung nhận diện
    cv2.imwrite(OUTPUT_PATH, img)
    print(f"--> Đã vẽ khung nhận diện và lưu kết quả tại: {OUTPUT_PATH}")
else:
    print("Không phát hiện được giai đoạn cây ngô nào thỏa mãn độ tự tin.")
print("-------------------------\n")