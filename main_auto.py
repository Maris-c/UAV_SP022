# main_auto.py
from auto_fly_control import *
import serial

def main():
    # Mở serial
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)

    print("\n=== AUTO FLY CONTROLLER ===")
    print("1. Check, Prearm, Arm, Disarm")
    print("2. Takeoff + Land")
    print("3. Takeoff + Forward + Backward + Land")
    mode = int(input("Chọn chế độ: "))

    match mode:
        # ==========================================
        # CASE 1
        # ==========================================
        case 1:
            print("\n--- MODE 1: ARM TEST ---")
            if not check_status(ser): return
            prearm(ser)
            arm(ser)
            disarm(ser)

        # ==========================================
        # CASE 2
        # ==========================================
        case 2:
            print("\n--- MODE 2: TAKEOFF + LAND ---")
            if not check_status(ser): return
            prearm(ser)
            arm(ser)
            takeoff(ser)
            land(ser)
            disarm(ser)

        # ==========================================
        # CASE 3
        # ==========================================
        case 3:
            print("\n--- MODE 3: AUTO FORWARD/BACKWARD ---")
            if not check_status(ser): return
            prearm(ser)
            arm(ser)
            takeoff(ser)
            move_forward(ser)
            move_backward(ser)
            land(ser)
            disarm(ser)

        # ==========================================
        # INVALID OPTION
        # ==========================================
        case _:
            print("Lựa chọn không hợp lệ!")

    ser.close()


if __name__ == "__main__":
    main()
