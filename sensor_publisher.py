#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import sys
import time
import random
from datetime import datetime
import threading
import logging
# Logging setup — single shared file for all sensors
logging.basicConfig(
    filename="sensors_publisher.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


# Usage:
#   python3 sensor_publisher.py <BROKER_IP> <TOPIC> <SENSOR_NAME>
#   Example: python3 sensor_publisher.py 10.0.0.2 sensors/pulse_oximeter pulse_oximeter
#   Example (all sensors): python3 sensor_publisher.py 10.0.0.2 sensors all

if len(sys.argv) != 4:
    print("Usage: python3 sensor_publisher.py <BROKER_IP> <TOPIC> <SENSOR_NAME>")
    sys.exit(1)

BROKER_IP = sys.argv[1]
TOPIC = sys.argv[2]
SENSOR_NAME = sys.argv[3].lower()
BROKER_PORT = 1883
LOG_FILE = f"/tmp/{SENSOR_NAME}_publisher.log"



# ============================================================
# ICU Traffic Classification Mapping (4 Categories)
# ============================================================
# Class 1 → Emergency & Important
# Class 2 → Emergency but Not Important
# Class 3 → Not Emergency but Important
# Class 4 → Not Emergency & Not Important  (Background/Admin)
# ============================================================

SENSOR_CONFIG = {
    # Class 1 - Emergency & Important
    "ecg_monitor": {"class": 1, "unit": "bpm", "min": 60, "max": 120, "interval": 1.0},
    "pulse_oximeter": {"class": 1, "unit": "%", "min": 85, "max": 100, "interval": 1.0},
    "bp_sensor": {"class": 1, "unit": "mmHg", "min": 90, "max": 180, "interval": 1.5},
    "fire_sensor": {"class": 1, "values": ["OK", "SMOKE_DETECTED", "FIRE_ALERT"], "interval": 1.0},

    # Class 2 - Emergency but Not Important
    "emg_sensor": {"class": 2, "unit": "mV", "min": 0, "max": 10, "interval": 1.5},
    "airflow_sensor": {"class": 2, "unit": "L/s", "min": 0, "max": 5, "interval": 2.0},
    "barometer": {"class": 2, "unit": "hPa", "min": 990, "max": 1030, "interval": 2.0},
    "smoke_sensor": {"class": 2, "values": ["CLEAR", "SMOKE_DETECTED"], "interval": 2.0},

    # Class 3 - Not Emergency but Important
    "infusion_pump": {"class": 3, "unit": "mL/hr", "min": 5, "max": 120, "interval": 2.5},
    "glucometer": {"class": 3, "unit": "mg/dL", "min": 70, "max": 180, "interval": 2.5},
    "gsr_sensor": {"class": 3, "unit": "µS", "min": 0.1, "max": 10, "interval": 2.5},

    # Class 4 - Not Emergency & Not Important
    "humidity_sensor": {"class": 4, "unit": "%", "min": 20, "max": 80, "interval": 3.0},
    "temperature_sensor": {"class": 4, "unit": "°C", "min": 20, "max": 35, "interval": 3.0},
    "co_sensor": {"class": 4, "unit": "ppm", "min": 0, "max": 50, "interval": 3.0},
}

# Short aliases
ALIASES = {
    "ecg": "ecg_monitor",
    "bp": "bp_sensor",
    "oxygen": "pulse_oximeter",
    "emg": "emg_sensor",
    "airflow": "airflow_sensor",
    "baro": "barometer",
    "smoke": "smoke_sensor",
    "infusion": "infusion_pump",
    "glucose": "glucometer",
    "gsr": "gsr_sensor",
    "humidity": "humidity_sensor",
    "temp": "temperature_sensor",
    "co": "co_sensor",
}


def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {msg}\n")
    print(f"[{timestamp}] {msg}", flush=True)


def publish_sensor(sensor_key, topic, broker_ip, broker_port):
    cfg = SENSOR_CONFIG[sensor_key]
    class_id = cfg["class"]
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    try:
        client.connect(broker_ip, broker_port)
        log(f"[Publisher] Connected to {broker_ip}:{broker_port}, topic '{topic}' as {sensor_key} (Class={class_id})")
    except Exception as e:
        log(f"[Publisher] Connection failed for {sensor_key}: {e}")
        return

    ADMIN_VALUES = ["sync", "idle", "config", "heartbeat_ok"]
    last_admin_time = time.time()
    ADMIN_INTERVAL = 15.0  # seconds

    while True:
        if "values" in cfg:
            value = random.choice(cfg["values"])
        else:
            value = round(random.uniform(cfg["min"], cfg["max"]), 2)

        payload = f"{sensor_key}:{value}{cfg.get('unit', '')}:Class={class_id}"

        try:
            client.publish(topic, payload)
            log(f"[Publisher] {sensor_key}: Published {payload}")
        except Exception as e:
            log(f"[Publisher] {sensor_key}: Publish failed: {e}")

        # Admin update
        if time.time() - last_admin_time >= ADMIN_INTERVAL:
            admin_topic = f"admin/{sensor_key}"
            admin_value = random.choice(ADMIN_VALUES)
            admin_payload = f"{sensor_key}:{admin_value}:Class=4"
            try:
                client.publish(admin_topic, admin_payload)
                log(f"[Publisher] (Admin) {admin_payload}")
                last_admin_time = time.time()
            except Exception as e:
                log(f"[Publisher] {sensor_key}: Admin publish failed: {e}")

        time.sleep(cfg["interval"])


def main():
    sensor_arg = sys.argv[3].lower()
    broker_ip = sys.argv[1]
    topic = sys.argv[2]

    # Run all sensors
    if sensor_arg == "all":
        log("[Publisher] Starting ALL sensors...")
        for sensor_name in SENSOR_CONFIG.keys():
            t = threading.Thread(
                target=publish_sensor,
                args=(sensor_name, topic, broker_ip, BROKER_PORT),
                daemon=True,
            )
            t.start()
        while True:
            time.sleep(1)
    else:
        # Run single sensor
        sensor_key = ALIASES.get(sensor_arg, sensor_arg)
        if sensor_key not in SENSOR_CONFIG:
            log(f"[Publisher] Unknown sensor '{SENSOR_NAME}', defaulting to humidity_sensor (Class 4)")
            sensor_key = "humidity_sensor"
        publish_sensor(sensor_key, topic, broker_ip, BROKER_PORT)


if __name__ == "__main__":

    main()
