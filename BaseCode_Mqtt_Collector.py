#!/usr/bin/env python3
"""
 Adding Senario2 code
 Ping and Ping burst

"""


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

import sys
import random
import threading
import signal

sys.stdout.reconfigure(line_buffering=True) #This forces real-time printing, so your output lines won’t appear indented or delayed.

# ================= Configuration =================
BROKER_PORT = 1883
BROKER_IP = "10.0.0.2"
OUTPUT_DIR = '/home/ictlab7/Documents/Learning_Mininet/PcapForExpt'
OUTPUT_LOG_DIR = '/home/ictlab7/Documents/Learning_Mininet/mqtt_capture'
MERGE_SWITCH_PCAPS = False
EXPERIMENT_SEED = 2029
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
"""
🟢 Scenario S2: IoT + Monitoring Traffic
Aspect	            Value                   	            Purpose
MQTT traffic          ✔     Measure baseline latency & jitter
iperf background     ❌      Validate emergency QoS without congestion
ping monitoring	     ✔      Lightweight realism
Emergency events	Rare    ping-only does not distort ML features much.
iperf background	❌
Congestion	      Minimal
"""
# =================================================



def start_ping_monitor(monitor, target_ip):
    log_file = f"{OUTPUT_LOG_DIR}/monitor_ping.log"
    cmd = f"ping {target_ip} > {log_file} 2>&1 &"
    monitor.cmd(cmd)
    info(f"📡 Ping monitoring started (monitor → {target_ip}), log: {log_file}\n")

def emergency_ping_bursts(host, target_ip, duration=120, prob=0.03):
    """
    Runs in background:
    For 'duration' seconds, occasionally triggers a short high-rate ping burst.
    prob = probability per second of an emergency event.
    """
    def runner():
        for _ in range(duration):
            if random.random() < prob:
                info("🚨 Emergency event triggered!\n")
                host.popen(
                    ["ping", "-c", "20", "-i", "0.05", target_ip],
                    stdout=open("/tmp/emergency_ping.log", "w"),
                    stderr=open("/tmp/emergency_ping.err", "w")
                )

            time.sleep(1)

    t = threading.Thread(target=runner, daemon=True)
    t.start()

# =================================================
# ================= Scenario S2 End ===============
# =================================================

# =================================================
# ================= Scenario S3 Start =============
# ================================================

"""
def start_iperf_server(host):
    host.cmd("iperf -s -u -D")
    info(f"📡 iperf UDP server started on {host.name}\n")

def start_moderate_iperf_background(src, dst_ip, rate="2M"):
    
    #Moderate background UDP load.
    #rate = 1–3 Mbps is ideal for 'partial congestion' on 10 Mbps links.
    
    cmd = f"iperf -u -c {dst_ip} -b {rate} -t 600 > /tmp/iperf_bg.log 2>&1 &"
    src.cmd(cmd)
    info(f"📶 Moderate iperf background started: {src.name} → {dst_ip} @ {rate}\n")
"""
# =================================================
# ================= Scenario S3 End ===============
# =================================================








def start_tcpdump(node, intf):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'{OUTPUT_DIR}/{node.name}_{intf}_{EXPERIMENT_SEED}_{timestamp}.pcap'
    node.cmd(f'tcpdump -i {intf} -w {filename} &')
    info(f'*** Capturing {intf} on {node.name} -> {filename}\n')
    return filename

def start_mqtt_broker(host):
    info('***Starting MQTT broker (Mosquitto)')
    conf_file = "/tmp/mosquitto.conf"
    host.cmd(f"echo 'listener {BROKER_PORT} 0.0.0.0\nallow_anonymous true' > {conf_file}")
    host.cmd(f"mosquitto -c {conf_file} -v &")
    time.sleep(3)
    info(f"✅ MQTT broker started at {BROKER_IP}:{BROKER_PORT}")

def start_mqtt_subscriber(monitor):
    log_file = f"{OUTPUT_LOG_DIR}/sensor_subscriber.log"
    cmd = f'python3 sensor_subscriber.py > {log_file} 2>&1 &'
    monitor.cmd(cmd)
    info(f"✅ MQTT subscriber started on Monitor node, logging to {log_file}")

def start_mqtt_publisher(host, sensor_name):
    log_file = f"{OUTPUT_LOG_DIR}/sensor_publisher_{sensor_name}.log"
    #cmd = f'python3 sensor_publisher.py {BROKER_IP} sensors/{sensor_name} {sensor_name} > {log_file} 2>&1 &'
    host.popen(
        ["python3", "sensor_publisher.py", BROKER_IP, "sensors", "all"],
        stdout=open(log_file, "w"),
        stderr=open(log_file.replace(".log", ".err"), "w")
    )
    info(f"✅ MQTT publisher started on {host.name} ({sensor_name}), logging to {log_file}\n")

# ==============================================================
def start_mqtt_network():
    net = Mininet(controller=Controller, switch=OVSSwitch, link=TCLink, autoSetMacs=True)

    # Controller
    info('\n*** Adding controller****')
    c0 = net.addController('c0')

    # Switches
    info('\n*** Adding switches*****')
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
    info('\n*** Creating links')
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
    info('\n*** Starting network')
    net.start()
    # Bring up interfaces
    for h in [broker, monitor, h1, h2, h3, h4, h5, h6, h7, h8,h9,h10,h11]:
        for intf in h.intfList():
            if 'lo' not in intf.name:
                h.cmd(f'ifconfig {intf} up')

    """
    # Start captures
    info('*** Starting tcpdump captures')
    for node in [broker, monitor, h2, h3, h4, h5, h6, h7, h8,h9,h10,h11]:
        for intf in node.intfList():
            if 'lo' not in intf.name:
                start_tcpdump(node, intf)
                
    """
    info('\n*** Starting tcpdump captures on main switches')

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
    # === IoT Sensor Class Mapping (14 hosts, realistic categories) ===

    # === Scenario S2 Additions  start ===
    # Continuous monitoring (baseline latency & jitter)
    #start_ping_monitor(monitor, BROKER_IP)
    # Rare emergency bursts from a critical sensor (e.g., ECG node h1)
    #emergency_ping_bursts(h1, BROKER_IP, duration=120, prob=0.05)
    # === Scenario S2 Additions  End ===

    # ================= Scenario S3 =================
    # Continuous monitoring
    start_ping_monitor(monitor, BROKER_IP)

    # Moderate emergency bursts (more frequent than S2)
    emergency_ping_bursts(h1, BROKER_IP, duration=180, prob=0.10)

    # Start iperf server on broker
    start_iperf_server(broker)

    # Moderate background load from a non-critical node
    # This creates partial congestion on S3–S1
    start_moderate_iperf_background(h12, BROKER_IP, rate="2M")

    # inside helper:
    # -t 600 instead of -t 0

    # === Scenario S3  End ===================








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
    info('\n*** Verifying connectivity')
    net.pingAll()
    info("\n*** Network is running. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
          info("\n*** Caught Ctrl+C, shutting down...\n")
    finally:

        info("\n*** Stopping background processes...\n")
        os.system("pkill -f iperf")
        os.system("pkill -f mosquitto")
        os.system("pkill -f tcpdump")
        os.system("pkill -f sensor_publisher.py")
        os.system("pkill -f ping")

        info("\n*** Stopping network")
        net.stop()
        info("\n*** Mininet simulation ended cleanly.")

    # CLI for manual testing
    #CLI(net)



if __name__ == '__main__':
    #setLogLevel('critical')
    setLogLevel('info')
    info("\n*************** Starting SDN IoT MQTT Topology ***************")
    start_mqtt_network()
