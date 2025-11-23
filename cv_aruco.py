import time, sys, select, json
import cv2, cv2.aruco as aruco
import numpy as np
from picamera2 import Picamera2

# ===============================
# === HÀM XỬ LÝ CHÍNH ===
# ===============================

def scan_aruco(frame, detector):
    gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
    corners, ids, _ = detector.detectMarkers(gray)
    return corners, ids


def send_data(timestamp, marker_id, detect_time_ms, detected_ids, log_data, mqtt_handler):
    """Gửi dữ liệu quét ArUco qua MQTT."""
    log_data.append((timestamp, marker_id))

    data = {
        "STT": len(log_data),
        "Aruco_ID": marker_id,
        "Detected_list": detected_ids,
        "Time": timestamp
    }

    json_data = json.dumps(data)
    mqtt_handler.publish("sp022/aruco", json_data)
    mqtt_handler.publish("sp022/log", json_data)
    print(f"[{timestamp}] Sent: {json_data}", flush=True)

    return log_data


def init_camera():
    picam2 = Picamera2()
    config = picam2.create_video_configuration(main={"size": (640, 480), "format": "RGB888"})
    picam2.configure(config)
    picam2.start()
    time.sleep(1)
    return picam2


def init_aruco():
    dictionary = aruco.getPredefinedDictionary(aruco.DICT_6X6_250)
    parameters = aruco.DetectorParameters()
    return aruco.ArucoDetector(dictionary, parameters)


def save_log_to_file(log_data, filename="aruco_log.csv"):
    with open(filename, "w") as f:
        f.write("Time,MarkerID\n")
        for t, mid in log_data:
            f.write(f"{t},{mid}\n")
    print(f"\nDữ liệu log đã lưu: {filename}", flush=True)


# ===============================
# === HÀM CHÍNH ===
# ===============================

def main(mqtt_handler):
    """Chương trình chính quét ArUco."""
    picam2 = init_camera()
    detector = init_aruco()
    last_detect_time = time.time()

    print("Camera đã sẵn sàng. Nhấn 'q' để thoát.\n", flush=True)

    last_detected_id = None
    detected_ids = []
    log_data = []

    try:
        while True:
            frame_rgb = picam2.capture_array()
            start_time = time.time()
            corners, ids = scan_aruco(frame_rgb, detector)
            detect_time_ms = (time.time() - start_time) * 1000

            if ids is not None:
                last_detect_time = time.time()
                for marker_id in ids.flatten():
                    marker_id = int(marker_id)
                    if marker_id not in detected_ids:
                        detected_ids.append(marker_id)
                        timestamp = time.strftime("%H:%M:%S")
                        log_data = send_data(timestamp, marker_id, detect_time_ms, detected_ids, log_data, mqtt_handler)
                        last_detected_id = marker_id
            cv2.imshow("Aruco Scanner", frame_rgb)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
               print("\Thoát chương trình...", flush=True)
               break

            if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                if sys.stdin.readline().strip().lower() == 'q':
                    print("\nThoát chương trình...", flush=True)
                    break

            if time.time() - last_detect_time > 180:
                print("\n⏸ Không phát hiện mã mới trong 180s, dừng chương trình...")
                break

    finally:
        picam2.stop()
        cv2.destroyAllWindows()
        save_log_to_file(log_data)
        print("Các ID đã phát hiện:", detected_ids, flush=True)
        print("Chương trình kết thúc.", flush=True)
