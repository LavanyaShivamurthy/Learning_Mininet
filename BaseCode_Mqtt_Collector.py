#!/usr/bin/env python3
from mininet.net import Mininet
from mininet.node import Controller, OVSSwitch
from mininet.link import TCLink
from mininet.log import setLogLevel, info
from mininet.cli import CLI
from datetime import datetime
import os
import time
import subprocess

# ================= Configuration =================
BROKER_PORT = 1883
BROKER_IP = "10.0.0.100"
#BROKER_IP = "127.0.0.1"
OUTPUT_DIR = '/home/ictlab7/Documents/Learning_Mininet/pcap_captures'
OUTPUT_LOG_DIR = '/home/ictlab7/Documents/Learning_Mininet/mqtt_capture'
MERGE_SWITCH_PCAPS = False  # Set True to enable merged switch PCAPs

# =================================================
# Ensure directories exist
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_LOG_DIR, exist_ok=True)

# =================================================
#automate  cleanup  (before creating the network):
os.system("mn -c")
os.system("pkill -f tcpdump")
os.system("pkill -f mosquitto")
# =================================================
# Cleanup previous Mininet state

def start_tcpdump(node, intf):
    """Start tcpdump on a node interface and return the filename."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'{OUTPUT_DIR}/{node.name}_{intf}_{timestamp}.pcap'
    node.cmd(f'tcpdump -i {intf} -w {filename} &')
    info(f'*** Capturing {intf} on {node.name} -> {filename}\n')
    return filename

def start_mqtt_broker(server):
    """Start MQTT broker on the server host."""
    info('*** Starting MQTT broker on server (with remote access)\n')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    conf_file = "/tmp/mosquitto.conf"
    #conf_file = f"/home/ictlab7/Documents/Learning_Mininet/mosquitto_file/mosquitto_{timestamp}.conf"
    server.cmd(f"echo 'listener {BROKER_PORT} 0.0.0.0\nallow_anonymous true' > {conf_file}")
    server.cmd(f"mosquitto -c {conf_file} -v &")
    time.sleep(4)
    # Check if broker is running
    if "mosquitto" in server.cmd(f"netstat -tulnp | grep {BROKER_PORT}"):
        info(f"✅ MQTT broker is running on {BROKER_IP}:{BROKER_PORT}\n")
    else:
        info("❌ Failed to start MQTT broker\n")

def start_mqtt_subscriber(server):
    """Start subscriber inside server host"""
    log_file = f"{OUTPUT_LOG_DIR}/sensor_subscriber.log"
    cmd = f'python3 sensor_subscriber.py {BROKER_IP} sensors/# > {log_file} 2>&1 &'
    server.cmd(cmd)
    info(f"✅ MQTT subscriber started on server, logging to {log_file}\n")

def start_mqtt_publisher(host, sensor_name):
    """Start publisher on a host and log output."""
    log_file = f"{OUTPUT_LOG_DIR}/sensor_publisher_{sensor_name}.log"
    cmd = f'python3 sensor_publisher.py {BROKER_IP} sensors/{sensor_name} {sensor_name} > {log_file} 2>&1 &'
    host.cmd(cmd)  # <<< THIS LINE WAS MISSING
    info(f"✅ MQTT publisher started on {host.name} ({sensor_name}), logging to {log_file}\n")
# ==============================================================
# Create network
# ==============================================================
def start_mqtt_network():
    net = Mininet(controller=Controller, switch=OVSSwitch, link=TCLink, autoSetMacs=True)

    # Add controller
    info('*** Adding controller\n')
    c0 = net.addController('c0')

    # Add hosts
    info('*** Adding hosts\n')
    emergency = net.addHost('emergency', ip='10.0.0.10/8')
    monitoring = net.addHost('monitoring', ip='10.0.0.20/8')
    server = net.addHost('server', ip='10.0.0.100/8')

    # Add switch
    info('*** Adding switch\n')
    s1 = net.addSwitch('s1')

    # Create links
    info('*** Creating links\n')
    net.addLink(emergency, s1, bw=10)
    net.addLink(monitoring, s1, bw=10)
    net.addLink(server, s1, bw=10)

    # Start network
    info('*** Starting network\n')
    net.start()
    # ==============================================================
    # Configure host interfaces
    # ==============================================================

    for h in [emergency, monitoring, server]:
        for intf in h.intfList():
            if 'lo' not in intf.name:
                h.cmd(f'ifconfig {intf} up')
    # ==============================================================
    # Clean old MQTT logs
    # ==============================================================
    for node in [server, emergency, monitoring]:
        node.cmd('rm -f /tmp/sensor_*.log')
    # ==============================================================
    # Start tcpdump on hosts
    # ==============================================================
    host_pcaps = {}
    for h in [emergency, monitoring, server]:
        for intf in h.intfList():
            if 'lo' not in intf.name:
                host_pcaps[f'{h.name}_{intf}'] = start_tcpdump(h, intf)
    # ==============================================================
    # Start tcpdump on switch interfaces
    # ==============================================================
    switch_pcaps = []
    for intf in s1.intfList():
        if 'lo' not in intf.name:
            switch_pcaps.append(start_tcpdump(s1, intf))
    # ==============================================================
    # Start tcpdump on controller
    # ==============================================================
    ctrl_pcap = start_tcpdump(c0, 'any')

    # Start MQTT broker
    start_mqtt_broker(server)
    # Test connectivity from emergency host
    test_conn = emergency.cmd(f"nc -zv {BROKER_IP} {BROKER_PORT}")
    if "succeeded" in test_conn:
        info("✅ Emergency host can reach the MQTT broker\n")
    else:
        info("⚠️ Emergency host cannot reach the broker\n")
    # ==============================================================
    # Start MQTT subscriber and publishers
    # ==============================================================
    start_mqtt_subscriber(server)
    time.sleep(2)  # small delay before starting publishers
    start_mqtt_publisher(emergency, "emergency")
    start_mqtt_publisher(monitoring, "monitoring")
    # ==============================================================
    # Verify connectivity
    # ==============================================================
    info('*** Verifying connectivity\n')
    net.pingAll()
    # ==============================================================
    # Start CLI
    # ==============================================================
    info('*** Starting CLI\n')
    CLI(net)
    # ==============================================================
    # Stop tcpdump processes
    # ==============================================================
    info('*** Stopping tcpdump\n')
    for h in [emergency, monitoring, server, s1, c0]:
        h.cmd('pkill tcpdump')
    # ==============================================================
    # Optional merge switch PCAPs
    # ==============================================================
    if MERGE_SWITCH_PCAPS and switch_pcaps:
        merged_filename = f'{OUTPUT_DIR}/{s1.name}_merged_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pcap'
        subprocess.run(['mergecap', '-w', merged_filename] + switch_pcaps)
        info(f'*** Merged switch PCAPs -> {merged_filename}\n')

    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    info("\n\n************************Starting Mininet********************************\n")
    start_mqtt_network()
