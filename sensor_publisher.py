import paho.mqtt.client as mqtt
import sys
import time
from datetime import datetime

# Usage: python3 sensor_publisher.py <BROKER_IP> <TOPIC> <SENSOR_NAME>

if len(sys.argv) != 4:
    print("Usage: python3 sensor_publisher.py <BROKER_IP> <TOPIC> <SENSOR_NAME>")
    sys.exit(1)

BROKER_IP = sys.argv[1]
TOPIC = sys.argv[2]
SENSOR_NAME = sys.argv[3]
BROKER_PORT = 1883
LOG_FILE = f"/tmp/{SENSOR_NAME}_publisher.log"

# Sample sensor data for demonstration
SENSOR_DATA_LIST = [
    "Temperature:25C",
    "Humidity:60%",
    "Pressure:1013hPa",
    "CO2:400ppm"
]

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {msg}\n")
    print(f"[{timestamp}] {msg}", flush= True)  # Optional stdout

def main():
    client = mqtt.Client()
    try:
        client.connect(BROKER_IP, BROKER_PORT)
        log(f"Connected to MQTT broker at {BROKER_IP}:{BROKER_PORT}, publishing to topic '{TOPIC}'")
    except Exception as e:
        log(f"Connection failed: {e}")
        sys.exit(1)

    while True:
        for data in SENSOR_DATA_LIST:
            payload = f"{SENSOR_NAME}: {data}"
            try:
                client.publish(TOPIC, payload)
                log(f"Published: {payload}")
            except Exception as e:
                log(f"Publish failed: {e}")
            time.sleep(1)  # Delay between messages

if __name__ == "__main__":
    main()

