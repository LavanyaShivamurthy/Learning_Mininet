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
OUTPUT_DIR = '/home/ictlab7/Documents/Learning_Mininet/pcap_captures'
MERGE_SWITCH_PCAPS = False #Set  True  to enable and  Set False to disable merging
SENSOR_TOPIC = "sensors/data"
TOPIC ="iot/data"
OUTPUT_LOG_DIR = '/home/ictlab7/Documents/Learning_Mininet/mqtt_capture'
os.makedirs(OUTPUT_DIR,exist_ok=True)
os.makedirs(OUTPUT_LOG_DIR,exist_ok=True)
# =================================================

def start_mqtt_network():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ==============================================================
    # Create network
    # ==============================================================
    net = Mininet(controller=Controller, switch=OVSSwitch, link=TCLink, autoSetMacs=True)
    
    info('*** Adding controller\n')
    c0 = net.addController('c0')
    
    info('*** Adding hosts\n')
    emergency = net.addHost('emergency', ip='10.0.0.10/8')
    monitoring = net.addHost('monitoring', ip='10.0.0.20/8')
    server = net.addHost('server', ip='10.0.0.100/8')
    
    info('*** Adding switch\n')
    s1 = net.addSwitch('s1')
    
    info('*** Creating links\n')
    net.addLink(emergency, s1, bw=10)
    net.addLink(monitoring, s1, bw=10)
    net.addLink(server, s1, bw=10)
    
    info('*** Starting network\n')
    net.start()
    
    # ==============================================================
    # Configure host interfaces
    # ==============================================================
    info('*** Configuring host interfaces\n')
    for h in [emergency, monitoring, server]:
        for intf in h.intfList():
            if 'lo' not in intf.name:
                h.cmd(f'ifconfig {intf} up')
    # =================================================
    # Cleaning old MQTT logs
    # =================================================
    info('*** Cleaning old MQTT logs\n')
    for node in [server, emergency, monitoring]:
        node.cmd('rm -f /tmp/sensor_*.log')
    # =================================================

    # ==============================================================
    # Start tcpdump on all hosts
    # ==============================================================
    info('*** Starting tcpdump on host interfaces\n')
    host_pcaps = {}
    for host_name in ['emergency', 'monitoring', 'server']:
        h = net.get(host_name)
        for intf in h.intfList():
            if 'lo' not in intf.name:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'{OUTPUT_DIR}/{host_name}_{intf}_{timestamp}.pcap'
                host_pcaps[f'{host_name}_{intf}'] = filename
                h.cmd(f'tcpdump -i {intf} -w {filename} &')
                info(f'*** Capturing {intf} on {host_name} -> {filename}\n')
    
    # ==============================================================
    # Start tcpdump on switch interfaces
    # ==============================================================
    info('*** Starting tcpdump on switch interfaces\n')
    switch_pcaps = []
    for intf in s1.intfList():
        if 'lo' not in intf.name:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'{OUTPUT_DIR}/{s1.name}_{intf}_{timestamp}.pcap'
            switch_pcaps.append(filename)
            s1.cmd(f'tcpdump -i {intf} -w {filename} &')
            info(f'*** Capturing {intf} on {s1.name} -> {filename}\n')
    
    # ==============================================================
    # Start tcpdump on controller
    # ==============================================================
    info('*** Starting tcpdump on controller\n')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    ctrl_pcap = f'{OUTPUT_DIR}/{c0.name}_any_{timestamp}.pcap'
    c0.cmd(f'tcpdump -i any -w {ctrl_pcap} &')
    info(f'*** Capturing controller -> {ctrl_pcap}\n')
    
    # ==============================================================
    # Start MQTT broker on server
    # ==============================================================
    info('*** Starting MQTT broker on server (with remote access)\n')

    # Create Mosquitto config file inside the server node
    server.cmd("echo 'listener 1883 0.0.0.0' > /tmp/mosquitto.conf")

    # Start Mosquitto with the custom config (verbose mode for logs)
    server.cmd("mosquitto -c /tmp/mosquitto.conf -d -v")

    # Give broker some time to initialize
    time.sleep(4)

    # Verify broker is listening
    broker_check = server.cmd("netstat -tulnp | grep 1883")
    if "mosquitto" in broker_check:
        info(f"✅ MQTT broker is running on {BROKER_IP}:1883\n")
    else:
        info("❌ Failed to start MQTT broker\n")

    # Optional: connectivity test from emergency node
    test_conn = emergency.cmd(f"nc -zv {BROKER_IP} 1883")
    if "succeeded" in test_conn:
        info("✅ Emergency host can reach the MQTT broker\n")
    else:
        info("⚠️ Emergency host cannot reach the broker\n")

    # ==============================================================
    # Start MQTT subscriber on server
    # ==============================================================
    info('*** Starting MQTT subscriber on server\n')
    lofg_file = f"{OUTPUT_LOG_DIR}/subscriber.log"
    server.cmd(f'python3 subscriber.py {BROKER_IP} {SENSOR_TOPIC} &')  # adjust path

    # ==============================================================
    # Start MQTT sensor publishers on emergency and monitoring hosts
    # Start MQTT Subscriber and Publishers with Logging
    # ==============================================================

    info('*** Starting MQTT subscriber on server (logs to /tmp/sensor_subscriber.log)\n')
    server.cmd(f'python3 sensor_subscriber.py sensors/# > /tmp/sensor_subscriber.log 2>&1 &')

    time.sleep(2)  # small delay before starting publishers

    info('*** Starting MQTT publishers on emergency and monitoring hosts (logs to /tmp/sensor_publisher_<host>.log)\n')

    # Start publisher on emergency
    emergency.cmd(
        f'python3 sensor_publisher.py {BROKER_IP} sensors/emergency emergency > /tmp/sensor_publisher_emergency.log 2>&1 &')

    # Start publisher on monitoring
    monitoring.cmd(
        f'python3 sensor_publisher.py {BROKER_IP} sensors/monitoring monitoring > /tmp/sensor_publisher_monitoring.log 2>&1 &')

    info('*** MQTT publishers and subscriber started with logging\n')

    # ==============================================================
    # Verify connectivity
    # ==============================================================
    info('*** Verifying connectivity\n')
    net.pingAll()
    
    # ==============================================================
    # Start CLI for interactive testing
    # ==============================================================
    info('*** Starting CLI\n')
    CLI(net)
    
    # ==============================================================
    # Stop tcpdump processes cleanly before exiting
    # ==============================================================
    info('*** Stopping tcpdump\n')
    for h in [emergency, monitoring, server, s1, c0]:
        h.cmd('pkill tcpdump')
    
    # ==============================================================
    # Optional: Merge switch PCAPs
    # ==============================================================
    if MERGE_SWITCH_PCAPS and switch_pcaps:
        merged_filename = f'{OUTPUT_DIR}/{s1.name}_merged_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pcap'
        merge_cmd = ['mergecap', '-w', merged_filename] + switch_pcaps
        subprocess.run(merge_cmd)
        info(f'*** Merged switch PCAPs -> {merged_filename}\n')
    
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    start_mqtt_network()

