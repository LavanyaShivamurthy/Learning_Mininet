import paho.mqtt.client as mqtt
from datetime import datetime

BROKER_IP = "10.0.0.100"
BROKER_PORT = 1883
TOPIC = "iot/data"
LOG_FILE = "/tmp/sensor_subscriber.log"

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {msg}\n")
    print(f"[{timestamp}] {msg}")  # optional stdout

def on_message(client, userdata, message):
    log(f"Received: {message.payload.decode()} on topic {message.topic}")

client = mqtt.Client()
client.on_message = on_message
client.connect(BROKER_IP, BROKER_PORT)
client.subscribe(TOPIC)
log("Subscriber connected and waiting for messages...")
client.loop_forever()

