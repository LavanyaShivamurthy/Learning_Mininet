#!/usr/bin/env python3
"""
S5_Mqtt_Collector.py — Class 2 + Class 3 Supplementary Capture
===============================================================
WHY THIS EXISTS:
  S1–S4 had insufficient Class 2 and Class 3 MQTT coverage.
  S5 captures both:
    • Class 2 (infusion_pump, glucometer, gsr_sensor) at 1.0s interval
    • Class 3 (emergency_button, vital_signs_monitor) at 0.5s interval

FIXES vs previous version:
  1. ifconfig bring-up runs BEFORE pingAll and publishers
  2. net.pingAll() replaced with net.ping([active hosts only])
     → eliminates the 200k+ ICMP flood from 14-host full mesh ping
  3. iperf background starts AFTER publishers so MQTT dominates early
  4. h13/h14 correctly included in interface bring-up loop
  5. Execution order: start → ifconfig → ping check → tcpdump →
     broker → publishers → iperf background → run loop

Architecture (same 3-switch topology as S1–S4):

              SDN Controller
                    |
                   S1 (Core)
                  /    \\
              S2          S3
          h1–h8 (idle)  h9–h14, broker, monitor
"""

from mininet.net import Mininet
from mininet.node import Controller, OVSSwitch
from mininet.link import TCLink
from mininet.log import setLogLevel, info
from datetime import datetime
import os
import sys
import time

sys.stdout.reconfigure(line_buffering=True)

# =====================================================================
# Configuration
# =====================================================================
BROKER_PORT     = 1883
BROKER_IP       = "10.0.0.2"
OUTPUT_DIR      = '/home/ictlab7/Documents/Learning_Mininet/PcapForExpt'
OUTPUT_LOG_DIR  = '/home/ictlab7/Documents/Learning_Mininet/mqtt_capture'
EXPERIMENT_SEED = 2025
SCENARIO_NAME   = "s5"

os.makedirs(OUTPUT_DIR,     exist_ok=True)
os.makedirs(OUTPUT_LOG_DIR, exist_ok=True)


# =====================================================================
# Helpers
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


def start_continuous_monitoring_publisher(host, sensor_name):
    """Launch a Class 2 sensor publisher (infusion_pump / glucometer / gsr_sensor)."""
    log_file = f"{OUTPUT_LOG_DIR}/sensor_publisher_{sensor_name}_s5.log"
    host.popen(
        ["python3", "S5_sensor_publisher.py", BROKER_IP, "sensors", sensor_name],
        stdout=open(log_file, "w"),
        stderr=open(log_file.replace(".log", ".err"), "w")
    )
    info(f"🟡 Class 2 publisher started: {sensor_name} on {host.name}\n")


def start_emergency_publisher(host, sensor_name):
    """Launch a Class 3 sensor publisher (emergency_button / vital_signs_monitor)."""
    log_file = f"{OUTPUT_LOG_DIR}/sensor_publisher_{sensor_name}_emergency_s5.log"
    host.popen(
        ["python3", "S5_sensor_publisher.py", BROKER_IP, "sensors", sensor_name],
        stdout=open(log_file, "w"),
        stderr=open(log_file.replace(".log", ".err"), "w")
    )
    info(f"🔴 Class 3 publisher started: {sensor_name} on {host.name}\n")


def start_ping_monitor(monitor, target_ip):
    log_file = f"{OUTPUT_LOG_DIR}/monitor_ping_s5.log"
    monitor.cmd(f"ping {target_ip} > {log_file} 2>&1 &")
    info(f"📡 Ping monitoring started (monitor → {target_ip})\n")


def start_iperf_server(host):
    host.cmd("iperf -s -u -D")
    info(f"📡 iperf UDP server started on {host.name}\n")


def start_light_iperf_background(src, dst_ip, rate="1M"):
    """Light background load — between S1 (none) and S2 (2M)."""
    cmd = f"iperf -u -c {dst_ip} -b {rate} -t 600 > /tmp/iperf_s5_bg.log 2>&1 &"
    src.cmd(cmd)
    info(f"📶 Light iperf background: {src.name} → {dst_ip} @ {rate}\n")


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

    # ── Broker + Monitor ─────────────────────────────────────────────
    broker  = net.addHost('broker',  ip='10.0.0.2/8')
    monitor = net.addHost('monitor', ip='10.0.0.3/8')

    # ── Idle hosts on S2 (topology identical to S1–S4) ───────────────
    h1  = net.addHost('h1',  ip='10.0.0.4/8')
    h2  = net.addHost('h2',  ip='10.0.0.5/8')
    h3  = net.addHost('h3',  ip='10.0.0.6/8')
    h4  = net.addHost('h4',  ip='10.0.0.7/8')
    h5  = net.addHost('h5',  ip='10.0.0.8/8')
    h6  = net.addHost('h6',  ip='10.0.0.9/8')
    h7  = net.addHost('h7',  ip='10.0.0.10/8')
    h8  = net.addHost('h8',  ip='10.0.0.11/8')

    # ── Class 2 sensor hosts on S3 ───────────────────────────────────
    h9  = net.addHost('h9',  ip='10.0.0.12/8')   # infusion_pump
    h10 = net.addHost('h10', ip='10.0.0.13/8')   # glucometer
    h11 = net.addHost('h11', ip='10.0.0.14/8')   # gsr_sensor

    # ── Background traffic host ───────────────────────────────────────
    h12 = net.addHost('h12', ip='10.0.0.15/8')

    # ── Class 3 sensor hosts on S3 ───────────────────────────────────
    h13 = net.addHost('h13', ip='10.0.0.16/8')   # emergency_button
    h14 = net.addHost('h14', ip='10.0.0.17/8')   # vital_signs_monitor

    # ── Links ─────────────────────────────────────────────────────────
    info('\n*** Creating links\n')
    net.addLink(s2, s1, bw=10)
    net.addLink(s3, s1, bw=10)

    net.addLink(broker,  s3, bw=10)
    net.addLink(monitor, s3, bw=10)

    for h in [h1, h2, h3, h4, h5, h6, h7, h8]:
        net.addLink(h, s2, bw=10)

    for h in [h9, h10, h11, h12, h13, h14]:
        net.addLink(h, s3, bw=10)

    # ── STEP 1: Start network ─────────────────────────────────────────
    info('\n*** Starting network\n')
    net.start()

    # ── STEP 2: Bring up ALL interfaces (h13/h14 included) ───────────
    # Must happen BEFORE pingAll and BEFORE publishers try to connect.
    info('\n*** Bringing up interfaces\n')
    for h in [broker, monitor, h1, h2, h3, h4, h5,
              h6, h7, h8, h9, h10, h11, h12, h13, h14]:
        for intf in h.intfList():
            if 'lo' not in intf.name:
                h.cmd(f'ifconfig {intf} up')
    time.sleep(1)

    # ── STEP 3: Targeted connectivity check (active hosts only) ───────
    # Replaces net.pingAll() which would generate 182 ICMP pairs
    # (14 hosts × 13) → 200k+ Class 0 packets drowning MQTT signal.
    info('\n*** Verifying connectivity (active sensor hosts → broker only)\n')
    net.ping([h9, h10, h11, h13, h14, broker])
    info("✅ Connectivity verified\n")

    # ── STEP 4: tcpdump on correct interfaces ─────────────────────────
    # KEY INSIGHT: h9–h14 and broker are ALL on s3.
    # MQTT traffic never crosses s1 — it stays entirely on s3.
    # Must capture on s3 eth interfaces, NOT s3 loopback (lo).
    #
    # Interface layout after net.start():
    #   s3-eth1 … s3-eth8  (one per host on s3: broker,monitor,h9–h14)
    #   s3-lo              (loopback — useless, don't capture here)
    #
    # Strategy: capture broker-eth0 (cleanest — one copy per MQTT packet)
    #           + s3-eth1 as backup (sees all s3 traffic)
    info('\n*** Starting tcpdump captures\n')
    # broker-eth0: primary MQTT capture — every sensor packet in/out
    start_tcpdump(broker, broker.defaultIntf())
    # s3 eth interfaces (skip loopback)
    for intf in s3.intfList():
        if 'lo' not in intf.name:
            start_tcpdump(s3, intf)
            break   # just the first eth port is enough
    # h13 for Class 3 verification
    start_tcpdump(h13, h13.defaultIntf())

    # ── STEP 5: MQTT broker + subscriber ─────────────────────────────
    start_mqtt_broker(broker)
    start_mqtt_subscriber(monitor)
    time.sleep(2)

    # ── STEP 6: Class 2 publishers ────────────────────────────────────
    start_continuous_monitoring_publisher(h9,  "infusion_pump")
    start_continuous_monitoring_publisher(h10, "glucometer")
    start_continuous_monitoring_publisher(h11, "gsr_sensor")
    info("🟡 Class 2 sensors publishing at 1.0s interval\n")
    time.sleep(2)   # let Class 2 publishers connect before Class 3 starts

    # ── STEP 7: Class 3 publishers ────────────────────────────────────
    start_emergency_publisher(h13, "emergency_button")
    start_emergency_publisher(h14, "vital_signs_monitor")
    info("🔴 Class 3 sensors publishing at 0.5s interval\n")
    time.sleep(2)   # let all publishers stabilise before background starts

    # ── STEP 8: Light background (iperf + ping monitor) ───────────────
    # Starts LAST so MQTT dominates the early part of the capture.
    start_ping_monitor(monitor, BROKER_IP)
    start_iperf_server(broker)
    start_iperf_server(h1)
    start_light_iperf_background(h12, h1.IP(), rate="1M")
    info("📶 S5: Light background activated (1M iperf)\n")

    info("\n*** S5 running — Ctrl+C to stop ***\n")

    # ── Run loop ──────────────────────────────────────────────────────
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
        os.system("pkill -f S5_sensor_publisher.py")
        os.system("pkill -f ping")
        info("\n*** Stopping network\n")
        net.stop()
        info("\n*** S5 simulation ended cleanly.\n")


if __name__ == '__main__':
    setLogLevel('info')
    info("\n*** Starting S5 — Class 2 + Class 3 Capture ***\n")
    start_s5_network()
