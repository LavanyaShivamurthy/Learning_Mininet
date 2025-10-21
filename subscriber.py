import paho.mqtt.client as mqtt

BROKER_IP = "10.0.0.100"  # server host IP inside Mininet
BROKER_PORT = 1883
TOPIC = "iot/data"

# Callback when a message is received
def on_message(client, userdata, message):
    print(f"[Subscriber] Received: {message.payload.decode()} on topic {message.topic}")

# Create client and connect
client = mqtt.Client()
client.on_message = on_message
client.connect(BROKER_IP, BROKER_PORT)

# Subscribe to the topic
client.subscribe(TOPIC)

# Start loop to process messages
client.loop_forever()

