#!/usr/bin/env python3
from mininet.net import Mininet
from mininet.node import Controller, OVSSwitch
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel
import threading
import time
import paho.mqtt.client as mqtt

# MQTT broker parameters
BROKER_IP = '10.0.0.100'
BROKER_PORT = 1883

# MQTT publisher function for a host
def mqtt_publish(host, topic, message, interval=2):
    def run():
        client = mqtt.Client()
        client.connect(BROKER_IP, BROKER_PORT)
        while True:
            client.publish(topic, message)
            time.sleep(interval)
    t = threading.Thread(target=run)
    t.daemon = True
    t.start()

def emergency_topology_mqtt():
    net = Mininet(controller=Controller, switch=OVSSwitch, link=TCLink, autoSetMacs=True)

    print("*** Starting controller")
    net.addController('c0')

    print("*** Adding hosts")
    emergency = net.addHost('emergency', ip='10.0.0.10/24')
    monitoring = net.addHost('monitoring', ip='10.0.0.20/24')
    server = net.addHost('server', ip='10.0.0.100/24')

    print("*** Adding switch")
    s1 = net.addSwitch('s1')

    print("*** Creating links with 10 Mbit bandwidth")
    net.addLink(emergency, s1, bw=10)
    net.addLink(monitoring, s1, bw=10)
    net.addLink(server, s1, bw=10)

    print("*** Starting network")
    net.start()

    print("*** Starting MQTT broker on server")
    server.cmd(f'mosquitto -p {BROKER_PORT} -d')

    print("*** Starting MQTT publishers on emergency and monitoring hosts")
    # Use Python function to simulate periodic MQTT publishing
    mqtt_publish(emergency, 'emergency/data', 'heartbeat=72')
    mqtt_publish(monitoring, 'monitoring/data', 'temp=36.6')

    print("*** Flushing ARP caches and verifying connectivity")
    for host in [emergency, monitoring, server]:
        host.cmd('arp -d')

    net.pingAll()

    print("*** Running CLI")
    CLI(net)

    print("*** Stopping network")
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    emergency_topology_mqtt()

