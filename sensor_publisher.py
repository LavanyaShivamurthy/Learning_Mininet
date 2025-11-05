#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import sys
import time
import random
from datetime import datetime

# Usage:
#   python3 sensor_publisher.py <BROKER_IP> <TOPIC> <SENSOR_NAME>

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

    # Class 3 - Not Emergency but Important
    "infusion_pump": {"class": 3, "unit": "mL/hr", "min": 5, "max": 120, "interval": 2.5},
    "glucometer": {"class": 3, "unit": "mg/dL", "min": 70, "max": 180, "interval": 2.5},
    "gsr_sensor": {"class": 3, "unit": "µS", "min": 0.1, "max": 10, "interval": 2.5},

    # Class 4 - Normal / Administrative
    "humidity_sensor": {"class": 4, "unit": "%", "min": 20, "max": 80, "interval": 3.0},
    "solar_sensor": {"class": 4, "unit": "W/m²", "min": 100, "max": 1000, "interval": 3.0},
    "admin_node": {"class": 4, "values": ["sync", "idle", "config"], "interval": 4.0},
}

# Allow short aliases for convenience
ALIASES = {
    "ecg": "ecg_monitor",
    "bp": "bp_sensor",
    "oxygen": "pulse_oximeter",
    "emg": "emg_sensor",
    "airflow": "airflow_sensor",
    "infusion": "infusion_pump",
    "glucose": "glucometer",
    "humidity": "humidity_sensor",
    "solar": "solar_sensor",
    "admin": "admin_node",
}


def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {msg}\n")
    print(f"[{timestamp}] {msg}", flush=True)


def main():
    # Resolve aliases
    sensor_key = ALIASES.get(SENSOR_NAME, SENSOR_NAME)
    if sensor_key not in SENSOR_CONFIG:
        log(f"[Publisher] Unknown sensor '{SENSOR_NAME}', defaulting to temp_sensor (Class 4)")
        sensor_key = "humidity_sensor"

    cfg = SENSOR_CONFIG[sensor_key]
    class_id = cfg["class"]

    # MQTT client (latest callback API)
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    try:
        client.connect(BROKER_IP, BROKER_PORT)
        log(f"[Publisher] Connected to {BROKER_IP}:{BROKER_PORT}, topic '{TOPIC}' as {SENSOR_NAME} (Class={class_id})")
    except Exception as e:
        log(f"[Publisher] Connection failed: {e}")
        sys.exit(1)

    # For random admin updates
    ADMIN_TOPICS = ["admin/sync", "admin/update", "admin/status"]
    ADMIN_VALUES = ["sync", "idle", "config", "heartbeat_ok"]

    last_admin_time = time.time()
    ADMIN_INTERVAL = 15.0  # seconds

    while True:
        # --- Publish main sensor data ---
        if "values" in cfg:
            value = random.choice(cfg["values"])
        else:
            value = round(random.uniform(cfg["min"], cfg["max"]), 2)
        payload = f"{SENSOR_NAME}:{value}{cfg.get('unit', '')}:Class={class_id}"

        try:
            client.publish(TOPIC, payload)
            log(f"[Publisher] Published: {payload}")
        except Exception as e:
            log(f"[Publisher] Publish failed: {e}")

        # --- Occasionally publish admin (Class 4) update ---
        if time.time() -last_admin_time >= ADMIN_INTERVAL :  # ~10% chance each cycle
            #admin_topic = random.choice(ADMIN_TOPICS)
            admin_topic = f"admin/{SENSOR_NAME}"
            admin_value = random.choice(ADMIN_VALUES)
            #admin_payload = f"admin_node:{admin_value}:Class=4"
            admin_payload = f"{SENSOR_NAME}:{admin_value}:Class=4"
            try:
                client.publish(admin_topic, admin_payload)
                log(f"[Publisher] (Admin Update) Published: {admin_payload}")
                last_admin_time = time.time()
            except Exception as e:
                log(f"[Publisher] Admin publish failed: {e}")

        time.sleep(cfg["interval"])


if __name__ == "__main__":
    main()
