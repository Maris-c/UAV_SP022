from mqtt_helper import MQTTHandler
from cv_aruco import main as run_aruco
import time
import json

def main():
    print("=== UAV ArUco Detection System ===")

    mqtt_handler = MQTTHandler("config.json")
    mqtt_handler.connect()

    mqtt_handler.publish("sp022/log", json.dumps({
        "status": "online",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "message": "SP022 system started"
    }))
    print("[LOG] SP022 system started.")

    run_aruco(mqtt_handler)

    mqtt_handler.publish("sp022/log", json.dumps({
        "status": "offline",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "message": "SP022 system stopped"
    }))
    mqtt_handler.disconnect()
    print("=== Kết thúc hệ thống UAV ===")

if __name__ == "__main__":
    main()



