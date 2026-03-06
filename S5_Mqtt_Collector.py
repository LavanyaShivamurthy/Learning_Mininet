#!/usr/bin/env python3
"""
S5 Scenario — Class 2 (Continuous Monitoring) Supplementary Capture
=====================================================================
WHY THIS EXISTS:
  infusion_pump, glucometer, gsr_sensor had only 46–65% MQTT coverage
  in S1–S4 because their publish interval was 2.5s (too slow → too few
  MQTT packets per TCP flow → fallback heuristic doing heavy lifting).

WHAT'S DIFFERENT vs S1–S4:
  1. Only Class 3 sensors active (infusion_pump, glucometer, gsr_sensor)
     → These are Class 2 in preprocessing (Continuous Monitoring)
  2. Publish interval: 1.0s  (was 2.5s)
  3. QoS: 1              (was 1 already — kept same, adds PUBACK traffic)
  4. 3 dedicated hosts per sensor (h9, h10, h11) — same IPs as S1–S4
  5. Background: light ping + single iperf stream (between S1 and S2 load)
  6. No emergency bursts (Class 3 sensors aren't emergency class)

HOW TO RUN:
  sudo python3 S5_Mqtt_Collector.py

OUTPUT:
  PcapForExpt/  →  .pcap files (same OUTPUT_DIR as S1–S4)
  Then convert with pcap_to_csv.sh (same as S1–S4)

Architecture (same 3-switch topology as S1–S4):

              SDN Controller
                    |
                   S1 (Core)
                  /    \
              S2          S3
          h1–h8        h9–h11, broker, monitor
"""

from mininet.net import Mininet
from mininet.node import Controller, OVSSwitch
from mininet.link import TCLink
from mininet.log import setLogLevel, info
from datetime import datetime
import os
import sys
import time
import random
import threading

sys.stdout.reconfigure(line_buffering=True)

# =====================================================================
# Configuration — matches S1–S4 exactly except OUTPUT paths + SEED
# =====================================================================
BROKER_PORT     = 1883
BROKER_IP       = "10.0.0.2"
OUTPUT_DIR      = '/home/ictlab7/Documents/Learning_Mininet/PcapForExpt'
OUTPUT_LOG_DIR  = '/home/ictlab7/Documents/Learning_Mininet/mqtt_capture'
EXPERIMENT_SEED = 2025   # keep same seed for reproducibility
SCENARIO_NAME   = "s5"

os.makedirs(OUTPUT_DIR,     exist_ok=True)
os.makedirs(OUTPUT_LOG_DIR, exist_ok=True)

"""
🟡 Scenario S5: Class 2 Continuous Monitoring Focus
=====================================================
Aspect              Value       Purpose
─────────────────────────────────────────────────────
MQTT traffic         ✔          Only infusion/glucometer/gsr
Sensor interval      1.0s       Was 2.5s → more packets per flow
iperf background     Light      1 stream @ 1M (between S1 and S2)
ping monitoring      ✔          Same as S2/S3
Emergency bursts     ❌         Class 2 sensors aren't emergency
Congestion           Minimal    Focus on clean Class 2 capture
Goal                 Push Class 2 MQTT coverage above 70%
"""


# =====================================================================
# Helpers (identical to BaseCode)
# =====================================================================


def start_tcpdump(node, intf):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename  = f'{OUTPUT_DIR}/{node.name}_{intf}_{EXPERIMENT_SEED}_{SCENARIO_NAME}_{timestamp}.pcap'
    node.cmd(f'tcpdump -i {intf} -w {filename} &')
    info(f'*** Capturing {intf} on {node.name} -> {filename}\n')
    return filename


def start_mqtt_broker(host):
    info('*** Starting MQTT broker (Mosquitto)\n')
    conf_file = "/tmp/mosquitto_s5.conf"
    host.cmd(f"echo 'listener {BROKER_PORT} 0.0.0.0\nallow_anonymous true' > {conf_file}")
    host.cmd(f"mosquitto -c {conf_file} -v &")
    time.sleep(3)
    info(f"✅ MQTT broker started at {BROKER_IP}:{BROKER_PORT}\n")


def start_mqtt_subscriber(monitor):
    log_file = f"{OUTPUT_LOG_DIR}/sensor_subscriber_s5.log"
    cmd      = f'python3 sensor_subscriber.py > {log_file} 2>&1 &'
    monitor.cmd(cmd)
    info(f"✅ MQTT subscriber started on monitor, log: {log_file}\n")


def start_mqtt_publisher_class2(host, sensor_name):
    """
    Launch sensor_publisher_s5.py for a SINGLE Class 3 sensor
    (infusion_pump / glucometer / gsr_sensor) at 1.0s interval.
    """
    log_file = f"{OUTPUT_LOG_DIR}/sensor_publisher_{sensor_name}_s5.log"
    host.popen(
        ["python3", "sensor_publisher_s5.py", BROKER_IP, "sensors", sensor_name],
        stdout=open(log_file, "w"),
        stderr=open(log_file.replace(".log", ".err"), "w")
    )
    info(f"✅ S5 publisher started on {host.name} ({sensor_name})\n")


def start_ping_monitor(monitor, target_ip):
    log_file = f"{OUTPUT_LOG_DIR}/monitor_ping_s5.log"
    monitor.cmd(f"ping {target_ip} > {log_file} 2>&1 &")
    info(f"📡 Ping monitoring started (monitor → {target_ip})\n")


def start_iperf_server(host):
    host.cmd("iperf -s -u -D")
    info(f"📡 iperf UDP server started on {host.name}\n")


def start_light_iperf_background(src, dst_ip, rate="1M"):
    """
    Light background load — between S1 (none) and S2 (2M).
    Keeps scenario realistic without drowning Class 2 MQTT traffic.
    """
    cmd = f"iperf -u -c {dst_ip} -b {rate} -t 600 > /tmp/iperf_s5_bg.log 2>&1 &"
    src.cmd(cmd)
    info(f"📶 Light iperf background: {src.name} → {dst_ip} @ {rate}\n")



def start_continuous_monitoring_publisher(host, sensor_name):
    """
    Launches sensor_publisher_s5.py for Class 2 (Continuous Monitoring) sensors
    Example sensors: infusion_pump, glucometer, gsr_sensor
    """
    log_file = f"{OUTPUT_LOG_DIR}/sensor_publisher_{sensor_name}_s5.log"
    host.popen(
        ["python3", "sensor_publisher_s5.py", BROKER_IP, "sensors", sensor_name],
        stdout=open(log_file, "w"),
        stderr=open(log_file.replace(".log", ".err"), "w")
    )
    info(f"Class 2 (Continuous Monitoring) publisher started: {sensor_name} on {host.name}\n")
    
def start_emergency_publisher(host, sensor_name):
    """
    Launches sensor_publisher_s5.py for Class 3 (Emergency Critical) sensors
    Example sensors: emergency_button, vital_signs_monitor, etc.
    """
    log_file = f"{OUTPUT_LOG_DIR}/sensor_publisher_{sensor_name}_emergency_s5.log"
    host.popen(
        ["python3", "sensor_publisher_s5.py", BROKER_IP, "sensors", sensor_name],
        stdout=open(log_file, "w"),
        stderr=open(log_file.replace(".log", ".err"), "w")
    )
    info(f"Class 3 (Emergency Critical) publisher started: {sensor_name} on {host.name}\n")
# =====================================================================
# Main topology + scenario
# =====================================================================

def start_s5_network():
    net = Mininet(controller=Controller, switch=OVSSwitch, link=TCLink, autoSetMacs=True)

    # ── Controller ────────────────────────────────────────────────────
    info('\n*** Adding controller\n')
    net.addController('c0')

    # ── Switches (same 3-switch topology as S1–S4) ────────────────────
    info('\n*** Adding switches\n')
    s1 = net.addSwitch('s1')
    s2 = net.addSwitch('s2')
    s3 = net.addSwitch('s3')

    # ── Broker + Monitor (same IPs as S1–S4) ─────────────────────────
    broker  = net.addHost('broker',  ip='10.0.0.2/8')
    monitor = net.addHost('monitor', ip='10.0.0.3/8')

    # ── Sensor hosts ──────────────────────────────────────────────────
    # h1–h8 on S2 (same as S1–S4, kept idle so topology is identical)
    h1  = net.addHost('h1',  ip='10.0.0.4/8')
    h2  = net.addHost('h2',  ip='10.0.0.5/8')
    h3  = net.addHost('h3',  ip='10.0.0.6/8')
    h4  = net.addHost('h4',  ip='10.0.0.7/8')
    h5  = net.addHost('h5',  ip='10.0.0.8/8')
    h6  = net.addHost('h6',  ip='10.0.0.9/8')
    h7  = net.addHost('h7',  ip='10.0.0.10/8')
    h8  = net.addHost('h8',  ip='10.0.0.11/8')

    # h9–h11 on S3 — these are the Class 2 sensor hosts
    h9  = net.addHost('h9',  ip='10.0.0.12/8')   # infusion_pump
    h10 = net.addHost('h10', ip='10.0.0.13/8')   # glucometer
    h11 = net.addHost('h11', ip='10.0.0.14/8')   # gsr_sensor

    # h12 on S3 — background traffic source (light iperf)
    h12 = net.addHost('h12', ip='10.0.0.15/8')

    # NEW: Add class 3 hosts on S3
    h13 = net.addHost('h13', ip='10.0.0.16/8')  # emergency_button
    h14 = net.addHost('h14', ip='10.0.0.17/8')  # vital_signs_monitor
    # ── Links (same bw=10 as S1–S4) ──────────────────────────────────
    info('\n*** Creating links\n')
    net.addLink(s2, s1, bw=10)
    net.addLink(s3, s1, bw=10)
    

    net.addLink(broker,  s3, bw=10)
    net.addLink(monitor, s3, bw=10)

    # S2 side (idle hosts — topology must be identical for feature consistency)
    for h in [h1, h2, h3, h4, h5, h6, h7, h8]:
        net.addLink(h, s2, bw=10)

    # S3 side (active Class 2 sensors + background)
    for h in [h9, h10, h11, h12, h13,h14]:
        net.addLink(h, s3, bw=10)

    # ── Start network ─────────────────────────────────────────────────
    info('\n*** Starting network\n')
    net.start()

    # Bring up interfaces
    for h in [broker, monitor, h1, h2, h3, h4, h5,
              h6, h7, h8, h9, h10, h11, h12]:
        for intf in h.intfList():
            if 'lo' not in intf.name:
                h.cmd(f'ifconfig {intf} up')

    # ── tcpdump on switches (same strategy as S1–S4) ──────────────────
    info('\n*** Starting tcpdump captures on main switches\n')

    for intf in s1.intfList():
        if 'lo' not in intf.name:
            start_tcpdump(s1, intf)

    start_tcpdump(s2, s2.intfList()[0])
    start_tcpdump(s3, s3.intfList()[0])
    
    info('\n*** Starting tcpdump on broker for MQTT verification ***\n')
    start_tcpdump(broker, broker.defaultIntf())  # broker-eth0

    # Optional: also on h13 (emergency_button host) for sender-side debug
    info('\n*** Starting tcpdump on h13 (emergency_button host) for debug ***\n')
    start_tcpdump(h13, h13.defaultIntf())  # h13-eth0

    # ── MQTT broker + subscriber ──────────────────────────────────────
    start_mqtt_broker(broker)
    start_mqtt_subscriber(monitor)
    time.sleep(2)

    # ── S5 scenario: light background only ───────────────────────────
    # Ping monitoring (same as S2/S3)
    start_ping_monitor(monitor, BROKER_IP)

    # Light iperf background from h12 (between S1-none and S2-2M load)
    start_iperf_server(broker)
    start_light_iperf_background(h12, BROKER_IP, rate="1M")

    info("📶 S5: Light background activated (1M iperf)\n")

    # ── Class 2 (Continuous Monitoring) sensors ONLY ─────────────────
    # Published by sensor_publisher_s5.py at 1.0s interval instead of 2.5s
    # ── Class 2 (Continuous Monitoring) sensors ───────────────────────
    start_continuous_monitoring_publisher(h9,  "infusion_pump")
    start_continuous_monitoring_publisher(h10, "glucometer")
    start_continuous_monitoring_publisher(h11, "gsr_sensor")

    info("🟡 Class 2 sensors (Monitoring) publishing at 1.0s interval\n")
    # ── Class 3 (Emergency Critical) sensors ──────────────────────────
    start_emergency_publisher(h13, "emergency_button")
    start_emergency_publisher(h14, "vital_signs_monitor")
    # Debug capture: directly on the emergency host (h13)
    info("*** Starting tcpdump on h13 (emergency_button host) for debug ***\n")
 
    # Add more emergency sensors here if you create them (h15, h16, ...)

    info("🔴 Class 3 sensors (Emergency) publishing — bursts possible\n")

    info("🟡 S5: Class 2 sensors publishing at 1.0s interval (was 2.5s)\n")

    # ── Connectivity check ────────────────────────────────────────────
    info('\n*** Verifying connectivity\n')
    net.pingAll()
    info("\n*** S5 network running. Press Ctrl+C to stop.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        info("\n*** Caught Ctrl+C, shutting down S5...\n")
    finally:
        info("\n*** Stopping background processes...\n")
        os.system("pkill -f iperf")
        os.system("pkill -f mosquitto")
        os.system("pkill -f tcpdump")
        os.system("pkill -f sensor_publisher_s5.py")
        os.system("pkill -f ping")

        info("\n*** Stopping network\n")
        net.stop()
        info("\n*** S5 simulation ended cleanly.\n")


if __name__ == '__main__':
    setLogLevel('info')
    info("\n*** Starting S5 — Class 2 Continuous Monitoring Scenario ***\n")
    start_s5_network()
