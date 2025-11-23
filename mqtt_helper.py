import paho.mqtt.client as mqtt
import json
import time

class MQTTHandler:
    def __init__(self, config_path="config.json"):
        with open(config_path, "r") as f:
            cfg = json.load(f)

        self.broker = cfg.get("mqtt_broker", "localhost")
        self.port = cfg.get("mqtt_port", 1883)
        self.user = cfg.get("mqtt_username", "")
        self.password = cfg.get("mqtt_password", "")
        self.client_id = cfg.get("mqtt_client_id", "aruco_publisher")
        self.lwt_topic = cfg.get("mqtt_lwt_topic", "system/status")

        self.client = mqtt.Client(client_id=self.client_id)
        if self.user and self.password:
            self.client.username_pw_set(self.user, self.password)

        self.client.will_set(self.lwt_topic, payload="offline", qos=1, retain=True)

    def connect(self):
        """Kết nối với broker và tự động thử lại nếu thất bại."""
        while True:
            try:
                self.client.connect(self.broker, self.port, 60)
                self.client.loop_start()
                print(f"[MQTT] Connected to {self.broker}:{self.port}")
                break
            except Exception as e:
                print(f"[MQTT] Lỗi kết nối: {e}, thử lại sau 3s...")
                time.sleep(3)

    def publish(self, topic, message):
        """Gửi dữ liệu MQTT"""
        try:
            self.client.publish(topic, message)
        except Exception as e:
            print(f"[MQTT] Lỗi gửi dữ liệu: {e}")

    def disconnect(self):
        """Ngắt kết nối"""
        try:
            self.client.loop_stop()
            self.client.disconnect()
            print("[MQTT] Ngắt kết nối thành công.")
        except Exception as e:
            print(f"[MQTT] Lỗi ngắt kết nối: {e}")



