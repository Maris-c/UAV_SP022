import serial
import struct
import time
import sys

############# Helper functions #############

def calculate_DVB_S2_checksum(data) -> int:
    checksum = 0x00
    for byte in data:
        checksum ^= byte
        for _ in range(8):
            if checksum & 0x80:
                checksum = (checksum << 1) ^ 0xD5
            else:
                checksum <<= 1
            checksum &= 0xFF
    return checksum

def CRC_DVB_S2_check(message) -> bool:
    if len(message) < 9:
        return False
    checksum = calculate_DVB_S2_checksum(message[3:-1])
    if checksum == message[-1]:
        return True
    else:
        print(f'CRC FAILED: got={message[-1]}, calc={checksum}')
        return False

def create_msp_request(function):
    message = bytearray(9)
    message[0:3] = b'$X<'
    message[3] = 0
    message[4] = function & 0xFF
    message[5] = (function >> 8) & 0xFF
    message[6] = 0
    message[7] = 0
    message[8] = calculate_DVB_S2_checksum(message[3:8])
    return bytes(message)

def create_msp_request_with_payload(function, payload_bytes):
    payload_size = len(payload_bytes)
    message = bytearray(9 + payload_size)
    message[0:3] = b'$X<'
    message[3] = 0
    message[4] = function & 0xFF
    message[5] = (function >> 8) & 0xFF
    message[6] = payload_size & 0xFF
    message[7] = (payload_size >> 8) & 0xFF
    message[8:8 + payload_size] = payload_bytes
    crc = calculate_DVB_S2_checksum(message[3:8 + payload_size])
    message[8 + payload_size] = crc
    return bytes(message)

def read_msp_response(ser, timeout=1.0):
    start_time = time.time()
    buffer = b''

    while time.time() - start_time < timeout:
        b = ser.read(1)
        if not b:
            continue
        buffer += b
        if len(buffer) > 64:
            buffer = buffer[-64:]

        idx = buffer.find(b'$X>')
        if idx != -1:
            buffer = buffer[idx:]
            break

    if not buffer.startswith(b'$X>'):
        return None

    needed = 8 - len(buffer)
    if needed > 0:
        buffer += ser.read(needed)
        if len(buffer) < 8:
            return None

    payload_size = buffer[6] + (buffer[7] << 8)
    remaining_len = payload_size + 1

    payload_and_crc = ser.read(remaining_len)
    start_wait = time.time()
    while len(payload_and_crc) < remaining_len and (time.time() - start_wait) < timeout:
        payload_and_crc += ser.read(remaining_len - len(payload_and_crc))

    if len(payload_and_crc) < remaining_len:
        return None

    return buffer[:8] + payload_and_crc

def parse_msp_response(message):
    if not message or not message.startswith(b'$X>'):
        return None, None
    function = message[4] + (message[5] << 8)
    payload = message[8:-1]
    return function, payload

######### Flight Control Setup ###############

SERIAL_PORT = '/dev/serial0'
BAUD_RATE = 115200

# MSP IDs
MSP_RAW_IMU = 102
MSP_RC = 105
MSP_STATUS = 101
MSP_ALTITUDE = 109
MSP_SET_RAW_RC = 200
MSP_GPS = 107

msp_rc = [1500] * 16

############ SEND RC #################

def send_rc_channels(ser, rc_channels):
    channels = list(rc_channels)[:16]
    if len(channels) < 16:
        channels += [1500] * (16 - len(channels))
    payload = b''.join(struct.pack('<H', int(ch)) for ch in channels)
    msg = create_msp_request_with_payload(MSP_SET_RAW_RC, payload)
    ser.write(msg)

############ STATUS CHECK #################

def check_status(ser, timeout=1.0):
    print(">>> CHECK STATUS")

    msg = create_msp_request(MSP_STATUS)
    ser.write(msg)

    response = read_msp_response(ser, timeout=timeout)
    if response is None:
        print("!!! NO RESPONSE FROM FC")
        return False

    if not CRC_DVB_S2_check(response):
        print("!!! CRC FAILED IN STATUS")
        return False

    fn, payload = parse_msp_response(response)
    if fn != MSP_STATUS:
        print(f"!!! WRONG FUNCTION ID: {fn}")
        return False

    print("STATUS OK")
    return True

############ FLIGHT FUNCTIONS #################

def prearm(ser, repeat=8, hold_time=0.12):
    print(">>> PREARM")
    for _ in range(repeat):
        msp_rc[6] = 1900
        msp_rc[2] = 1000
        send_rc_channels(ser, msp_rc)
        time.sleep(hold_time)

def arm(ser, repeat=10, hold_time=0.12):
    print(">>> ARMING")
    for _ in range(repeat):
        msp_rc[4] = 1900
        msp_rc[6] = 1900
        msp_rc[2] = 1000
        send_rc_channels(ser, msp_rc)
        time.sleep(hold_time)

def disarm(ser, repeat=10, hold_time=0.12):
    print(">>> DISARM")
    for _ in range(repeat):
        msp_rc[4] = 1100
        msp_rc[6] = 1100
        msp_rc[2] = 1000
        send_rc_channels(ser, msp_rc)
        time.sleep(hold_time)

def throttle_up(ser, repeat=40, hold_time=0.12):
    print(">>> TAKEOFF")
    msp_rc[2] = 1000
    for _ in range(repeat):
        if msp_rc[2] < 1200:
            msp_rc[2] += 5
        send_rc_channels(ser, msp_rc)
        time.sleep(hold_time)

def throttle_down(ser, repeat=40, hold_time=0.12):
    print(">>> LANDING")
    for _ in range(repeat):
        if msp_rc[2] > 1000:
            msp_rc[2] -= 5
        send_rc_channels(ser, msp_rc)
        time.sleep(hold_time)

def takeoff(ser):
    throttle_up(ser)

def land(ser):
    throttle_down(ser)

def move_forward(ser, power=1550, duration=1.0):
    print(">>> MOVE FORWARD")
    msp_rc[1] = power
    end = time.time() + duration
    while time.time() < end:
        send_rc_channels(ser, msp_rc)
        time.sleep(0.05)
    msp_rc[1] = 1500
    send_rc_channels(ser, msp_rc)

def move_backward(ser, power=1450, duration=1.0):
    print(">>> MOVE BACKWARD")
    msp_rc[1] = power
    end = time.time() + duration
    while time.time() < end:
        send_rc_channels(ser, msp_rc)
        time.sleep(0.05)
    msp_rc[1] = 1500
    send_rc_channels(ser, msp_rc)
