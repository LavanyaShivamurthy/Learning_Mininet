import time
import paho.mqtt.client as mqtt
import random

BROKER_IP = "10.0.0.100"  # server host IP inside Mininet
BROKER_PORT = 1883
TOPIC = "iot/data"

# Create client and connect
client = mqtt.Client()
client.connect(BROKER_IP, BROKER_PORT)

# Publish some messages every second
for i in range(10):
    payload = f"Data {i} from host"
    client.publish(TOPIC, payload)
    print(f"[Publisher] Sent: {payload}")
    time.sleep(1)

client.disconnect()

