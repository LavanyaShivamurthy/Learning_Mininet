import sys, time
import paho.mqtt.client as mqtt
from datetime import datetime

BROKER_IP = "10.0.0.100"

#BROKER_IP = sys.argv[1]
BROKER_PORT = 1883
TOPIC = "sensors/#"
LOG_FILE = "/home/ictlab7/Documents/Learning_Mininet/mqtt_capture/sensor_subscriber.log"

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {msg}\n")
    print(f"[{timestamp}] {msg}", flush=True)

def on_connect(client, userdata, flags, reason_code, properties=None):
    log(f"[Subscriber] Connected with result code {reason_code}")
    client.subscribe(TOPIC)

def on_message(client, userdata, message):
    payload = message.payload.decode()
    topic = message.topic
    log(f"[Subscriber] Received: {payload} on topic {topic}")

if __name__ == "__main__":
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message

    log("[Subscriber] Connecting to broker...")
    client.connect(BROKER_IP, BROKER_PORT)
    client.loop_forever()
