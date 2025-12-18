#!/usr/bin/env python3
"""
Three-Switch SDN IoT Topology with MQTT Communication
------------------------------------------------------
Architecture Summary:

              +----------------------+
              |     SDN Controller                  |
              |   (OpenFlow reference controller)    |
              +----------+-----------+
                         |
                    (OpenFlow)
                         |
               +---------+----------+
               |        S1          |
               |   (Core Switch)    |
               +---------+----------+
                  |             |
     +------------+             +-------------+
     |                                          |
+----+----+                                +----+----+
|   S2    |                                |   S3    |
| (Access)|                                | (Access)|
+----+----+                                +----+----+
     |                                          |
  h2–h7 IoT hosts,                          h8–h14 IoT hosts, broker, Monitor
     |                                          |
     +-----------------+------------------------+
                       |
                MQTT Broker (10.0.0.2)
                + Monitor Node (10.0.0.10)
"""

from mininet.net import Mininet
from mininet.node import Controller, OVSSwitch
from mininet.link import TCLink
from mininet.log import setLogLevel, info
from mininet.cli import CLI
from datetime import datetime
import os
import time
import subprocess
import sys
sys.stdout.reconfigure(line_buffering=True) #This forces real-time printing, so your output lines won’t appear indented or delayed.

# ================= Configuration =================
BROKER_PORT = 1883
BROKER_IP = "10.0.0.2"
OUTPUT_DIR = '/home/ictlab7/Documents/Learning_Mininet/pcap_captures'
OUTPUT_LOG_DIR = '/home/ictlab7/Documents/Learning_Mininet/mqtt_capture'
MERGE_SWITCH_PCAPS = False

# =================================================
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_LOG_DIR, exist_ok=True)

# Cleanup any old Mininet state
"""
os.system("mn -c")
os.system("pkill -f tcpdump")
os.system("pkill -f mosquitto")
"""
# =================================================
def start_tcpdump(node, intf):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'{OUTPUT_DIR}/{node.name}_{intf}_{timestamp}.pcap'
    node.cmd(f'tcpdump -i {intf} -w {filename} &')
    info(f'*** Capturing {intf} on {node.name} -> {filename}\n')
    return filename

def start_mqtt_broker(host):
    info('***Starting MQTT broker (Mosquitto)\n')
    conf_file = "/tmp/mosquitto.conf"
    host.cmd(f"echo 'listener {BROKER_PORT} 0.0.0.0\nallow_anonymous true' > {conf_file}")
    host.cmd(f"mosquitto -c {conf_file} -v &")
    time.sleep(3)
    info(f"✅ MQTT broker started at {BROKER_IP}:{BROKER_PORT}\n")

def start_mqtt_subscriber(monitor):
    log_file = f"{OUTPUT_LOG_DIR}/sensor_subscriber.log"
    cmd = f'python3 sensor_subscriber.py > {log_file} 2>&1 &'
    monitor.cmd(cmd)
    info(f"✅ MQTT subscriber started on Monitor node, logging to {log_file}\n")

def start_mqtt_publisher(host, sensor_name):
    log_file = f"{OUTPUT_LOG_DIR}/sensor_publisher_{sensor_name}.log"
    #cmd = f'python3 sensor_publisher.py {BROKER_IP} sensors/{sensor_name} {sensor_name} > {log_file} 2>&1 &'
    cmd = f'python3 sensor_publisher.py {BROKER_IP} sensors all'
    host.cmd(cmd)
    info(f"✅ MQTT publisher started on {host.name} ({sensor_name}), logging to {log_file}\n")

# ==============================================================
def start_mqtt_network():
    net = Mininet(controller=Controller, switch=OVSSwitch, link=TCLink, autoSetMacs=True)

    # Controller
    info('*** Adding controller\n')
    c0 = net.addController('c0')

    # Switches
    info('*** Adding switches\n')
    s1 = net.addSwitch('s1')
    s2 = net.addSwitch('s2')
    s3 = net.addSwitch('s3')

    # Broker + Monitor (on same node for simplicity)
    broker = net.addHost('broker', ip='10.0.0.2/8')
    monitor = net.addHost('monitor', ip='10.0.0.3/8')

    # IoT hosts (sensors)
    h1 = net.addHost('h1', ip='10.0.0.4/8')
    h2 = net.addHost('h2', ip='10.0.0.5/8')
    h3 = net.addHost('h3', ip='10.0.0.6/8')
    h4 = net.addHost('h4', ip='10.0.0.7/8')
    h5 = net.addHost('h5', ip='10.0.0.8/8')
    h6 = net.addHost('h6', ip='10.0.0.9/8')
    h7 = net.addHost('h7', ip='10.0.0.10/8')
    h8 = net.addHost('h8', ip='10.0.0.11/8')
    h9 = net.addHost('h9', ip='10.0.0.12/8')
    h10 = net.addHost('h10', ip='10.0.0.13/8')
    h11 = net.addHost('h11', ip='10.0.0.14/8')
    h12 = net.addHost('h12', ip='10.0.0.12/8')
    h13 = net.addHost('h13', ip='10.0.0.13/8')
    h14 = net.addHost('h14', ip='10.0.0.14/8')

    # Links
    info('*** Creating links\n')
    net.addLink(s2, s1, bw=10)
    net.addLink(s3, s1, bw=10)

    net.addLink(broker, s3, bw=10)
    net.addLink(monitor, s3, bw=10)

    net.addLink(h1, s2, bw=10)
    net.addLink(h2, s2, bw=10)

    net.addLink(h3, s2, bw=10)
    net.addLink(h4, s2, bw=10)
    net.addLink(h5, s2, bw=10)
    net.addLink(h6, s2, bw=10)
    net.addLink(h7, s2, bw=10)

    net.addLink(h8, s3, bw=10)
    net.addLink(h9, s3, bw=10)
    net.addLink(h10, s3, bw=10)
    net.addLink(h11, s3, bw=10)
    net.addLink(h12, s3, bw=10)
    net.addLink(h13, s3, bw=10)
    net.addLink(h14, s3, bw=10)
    info('*** Starting network\n')
    net.start()
    # Bring up interfaces
    for h in [broker, monitor, h1, h2, h3, h4, h5, h6, h7, h8,h9,h10,h11]:
        for intf in h.intfList():
            if 'lo' not in intf.name:
                h.cmd(f'ifconfig {intf} up')

    """
    # Start captures
    info('*** Starting tcpdump captures\n')
    for node in [broker, monitor, h2, h3, h4, h5, h6, h7, h8,h9,h10,h11]:
        for intf in node.intfList():
            if 'lo' not in intf.name:
                start_tcpdump(node, intf)
                
    """
    info('*** Starting tcpdump captures on main switches\n')

    # Capture from core switch s1 (all flows)
    for intf in s1.intfList():
        if 'lo' not in intf.name:
            start_tcpdump(s1, intf)

    # Capture from edge switch s2 (sensor side)
    start_tcpdump(s2, s2.intfList()[0])

    # Capture from edge switch s3 (broker side)
    start_tcpdump(s3, s3.intfList()[0])

    # Start MQTT system
    start_mqtt_broker(broker)
    start_mqtt_subscriber(monitor)

    time.sleep(2)
    """
    start_mqtt_publisher(h1, "admin_node")
    start_mqtt_publisher(h2, "admin_node")
    start_mqtt_publisher(h3, "pulse_oximeter")
    start_mqtt_publisher(h4, "bp_sensor")
    start_mqtt_publisher(h5, "emg_sensor")
    start_mqtt_publisher(h6, "humidity_sensor")
    start_mqtt_publisher(h7, "airflow_sensor")
    start_mqtt_publisher(h8, "glucometer")
    start_mqtt_publisher(h9, "solar_sensor")
    start_mqtt_publisher(h10, "infusion_pump")
    start_mqtt_publisher(h11, "ecg_monitor")
    """
    # === IoT Sensor Class Mapping (14 hosts, realistic categories) ===

    # Class 1 – Emergency & Important
    start_mqtt_publisher(h1, "ecg_monitor")  # continuous cardiac data
    start_mqtt_publisher(h2, "pulse_oximeter")  # blood oxygen emergency
    start_mqtt_publisher(h3, "bp_sensor")  # sudden BP changes
    start_mqtt_publisher(h4, "fire_sensor")  # immediate emergency alert

    # Class 2 – Emergency but Not Important
    start_mqtt_publisher(h5, "emg_sensor")  # sudden muscle contraction alert
    start_mqtt_publisher(h6, "airflow_sensor")  # breathing irregularity
    start_mqtt_publisher(h7, "barometer")  # pressure anomaly indicator
    start_mqtt_publisher(h8, "smoke_sensor")  # hazard warning (non-medical)

    # Class 3 – Not Emergency but Important
    start_mqtt_publisher(h9, "infusion_pump")  # medicine delivery rate
    start_mqtt_publisher(h10, "glucometer")  # periodic glucose level
    start_mqtt_publisher(h11, "gsr_sensor")  # skin response sensor

    # Class 4 – Not Emergency & Not Important (environmental / background)
    start_mqtt_publisher(h12, "humidity_sensor")
    start_mqtt_publisher(h13, "temperature_sensor")
    start_mqtt_publisher(h14, "co_sensor")  # carbon monoxide background

    # Note:
    # - Each sensor sends MQTT packets to the broker running on the controller or a specific host.
    # - Your sensor_publisher.py already randomizes delay + injects admin Class=4 messages occasionally.
    # - This ensures you have all 4 classes represented in network traffic.

    # Connectivity test
    info('*** Verifying connectivity')
    net.pingAll()
    info("*** Running automated test and then shutting down...\n")
    time.sleep(30)  # Allow MQTT traffic to flow for 10s

    info("*** Stopping network")
    net.stop()
    info("*** Mininet simulation ended cleanly.")

    # CLI for manual testing
    #CLI(net)



if __name__ == '__main__':
    #setLogLevel('critical')
    setLogLevel('info')
    info("*************** Starting SDN IoT MQTT Topology ***************")
    start_mqtt_network()
