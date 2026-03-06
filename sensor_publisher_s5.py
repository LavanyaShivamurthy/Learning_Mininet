#!/usr/bin/env python3
"""
sensor_publisher_s5.py — Class 2 (Continuous Monitoring) Only
==============================================================
Identical to sensor_publisher.py EXCEPT:
  1. Only infusion_pump, glucometer, gsr_sensor are defined
  2. Publish interval: 1.0s  (was 2.5s in original)
  3. Must be called with a specific sensor name, not "all"
     e.g.  python3 sensor_publisher_s5.py 10.0.0.2 sensors infusion_pump

WHY: These 3 sensors had 46–65% MQTT coverage in S1–S4 because 2.5s
     interval means very few MQTT packets per TCP flow window. At 1.0s,
     each flow will contain 2.5× more MQTT PUBLISH+PUBACK pairs, pushing
     coverage above the 70% threshold.
"""

from logging.handlers import TimedRotatingFileHandler
import paho.mqtt.client as mqtt
import sys
import time
import random
from datetime import datetime
import threading
import logging
import signal

# ── Reproducibility ──────────────────────────────────────────────────────────
EXPERIMENT_SEED = 2025
random.seed(EXPERIMENT_SEED)

stop_event = threading.Event()

def handle_exit(sig, frame):
    print("\n[INFO] Ctrl+C received. Stopping S5 publisher...")
    stop_event.set()

signal.signal(signal.SIGINT, handle_exit)

# ── Logging (same rotation as original) ──────────────────────────────────────
handler = TimedRotatingFileHandler(
    "sensors_publisher_s5.log",
    when="H", interval=1, backupCount=48
)
logging.basicConfig(
    handlers=[handler],
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# ── Args ──────────────────────────────────────────────────────────────────────
if len(sys.argv) != 4:
    print("Usage: python3 sensor_publisher_s5.py <BROKER_IP> <TOPIC> <SENSOR_NAME>")
    print("  SENSOR_NAME must be one of: infusion_pump, glucometer, gsr_sensor")
    sys.exit(1)

BROKER_IP   = sys.argv[1]
TOPIC       = sys.argv[2]
SENSOR_NAME = sys.argv[3].lower()
BROKER_PORT = 1883
LOG_FILE    = f"/tmp/{SENSOR_NAME}_s5_publisher.log"

# ── S5 Sensor Config — Class 3 sensors only, interval reduced to 1.0s ────────
#
#  NOTE ON CLASS NUMBERS:
#  sensor_publisher.py uses Class 1–4 (original 4-class scheme).
#  preprocessing uses Class 0–3 (remapped). The SENSOR_CONFIG in
#  preprossing_v6.py maps these sensors to class=2 (Continuous Monitoring).
#  We keep Class=3 in the payload to match S1–S4 payload format exactly.
#
SENSOR_CONFIG = {
    "infusion_pump": {
        "class"   : 3,                     # matches S1–S4 payload format
        "unit"    : "mL/hr",
        "min"     : 5,
        "max"     : 120,
        "interval": 1.0,                   # ← KEY CHANGE: was 2.5s
    },
    "glucometer": {
        "class"   : 3,
        "unit"    : "mg/dL",
        "min"     : 70,
        "max"     : 180,
        "interval": 1.0,                   # ← KEY CHANGE: was 2.5s
    },
    "gsr_sensor": {
        "class"   : 3,
        "unit"    : "µS",
        "min"     : 0.1,
        "max"     : 10,
        "interval": 1.0,                   # ← KEY CHANGE: was 2.5s
    },
    # ── Class 3 (Emergency Critical) ─────────────────────────────────
    "emergency_button": {
        "class"   : 4,           # maps to priority_class = 3 in preprocessing
        "unit"    : "alert",
        "min"     : 0,
        "max"     : 1,
        "interval": 0.5,         # faster publishing for urgency
    },
    "vital_signs_monitor": {
        "class"   : 4,
        "unit"    : "bpm",
        "min"     : 60,
        "max"     : 180,
        "interval": 0.5,
    },
}

ALIASES = {
    "infusion" : "infusion_pump",
    "glucose"  : "glucometer",
    "gsr"      : "gsr_sensor",
}

ADMIN_VALUES   = ["sync", "idle", "config", "heartbeat_ok"]
ADMIN_INTERVAL = 15.0   # same as original


def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {msg}\n")
    print(f"[{timestamp}] {msg}", flush=True)


def publish_sensor(sensor_key, topic, broker_ip, broker_port):
    cfg      = SENSOR_CONFIG[sensor_key]
    class_id = cfg["class"]

    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)

    # Deterministic per-sensor seed (same formula as original)
    sensor_seed = EXPERIMENT_SEED + hash(sensor_key) % 10000
    rng = random.Random(sensor_seed)

    try:
        client.connect(broker_ip, broker_port)
        log(f"[Publisher] Connected to {broker_ip}:{broker_port}, "
            f"topic '{topic}' as {sensor_key} (Class={class_id}, interval={cfg['interval']}s)")
        client.loop_start()
    except Exception as e:
        log(f"[Publisher] Connection failed for {sensor_key}: {e}")
        return

    sensor_topic    = f"sensor/{sensor_key}"
    last_admin_time = time.time()

    while not stop_event.is_set():
        # Generate reading (same format as S1–S4)
        value   = round(rng.uniform(cfg["min"], cfg["max"]), 2)
        payload = f"{sensor_key}:{value}{cfg['unit']}:Class={class_id}"

        try:
            client.publish(sensor_topic, payload, qos=1)
            log(f"[Publisher] {sensor_key}: {payload}")
        except Exception as e:
            log(f"[Publisher] {sensor_key}: Publish failed: {e}")

        # Admin heartbeat — same 15s cadence as original
        if time.time() - last_admin_time >= ADMIN_INTERVAL:
            admin_value = rng.choice(ADMIN_VALUES)
            try:
                client.publish("admin/heartbeat", admin_value, qos=0)
                log(f"[Publisher] (Admin) {admin_value}")
                last_admin_time = time.time()
            except Exception as e:
                log(f"[Publisher] {sensor_key}: Admin publish failed: {e}")

        log(f"[SeedConfig] Sensor={sensor_key}, Seed={sensor_seed}")
        time.sleep(cfg["interval"])   # 1.0s instead of 2.5s

    client.loop_stop()
    client.disconnect()
    log(f"[Publisher] {sensor_key}: Stopped cleanly.")


def main():
    sensor_arg = sys.argv[3].lower()
    broker_ip  = sys.argv[1]
    topic      = sys.argv[2]

    # Resolve alias
    sensor_key = ALIASES.get(sensor_arg, sensor_arg)

    if sensor_key not in SENSOR_CONFIG:
        log(f"[Publisher] ERROR: Unknown sensor '{sensor_arg}'.")
        log(f"[Publisher] Valid sensors: {list(SENSOR_CONFIG.keys())}")
        sys.exit(1)

    log(f"[Publisher] Starting S5 publisher for: {sensor_key} "
        f"(interval={SENSOR_CONFIG[sensor_key]['interval']}s, qos=1)")
    publish_sensor(sensor_key, topic, broker_ip, BROKER_PORT)


if __name__ == "__main__":
    main()
