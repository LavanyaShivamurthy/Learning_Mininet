""" 
Modified BaseCode with embedded dual-port TCP (6000) + UDP (5555) server running inside Mininet 'server' node.
Keeps netcat on 5001 for imaging traffic and retains tcpdump for packet capture.
"""

from mininet.net import Mininet
from mininet.topo import Topo
from mininet.node import Controller, OVSSwitch
from mininet.link import TCLink
from mininet.log import setLogLevel, info
from mininet.cli import CLI
import os
import time
from time import sleep
from datetime import datetime
import threading
from numpy import random
import signal
import socket
import sys
import subprocess

# Global configuration
server_ip = "10.0.0.100"
udp_port = 5555
tcp_port = 6000
sensor_data = "Temperature:25C"


# Restart OVS services to ensure DB is available
os.system("sudo systemctl restart openvswitch-switch")

# Remove leftover bridges (optional, safer)
for br in os.popen("sudo ovs-vsctl list-br").read().split():
    os.system(f"sudo ovs-vsctl del-br {br}")



class customTopology(Topo):
    def build(self):
        info('*** Adding switches\n')
        s1 = self.addSwitch('s1', protocols='OpenFlow13')

        info('*** Adding medical devices/hosts\n')
        emergency = self.addHost('emergency', ip='10.0.0.10')
        monitoring = self.addHost('monitoring', ip='10.0.0.20')
        server = self.addHost('server', ip=server_ip)

        self.addLink(emergency, s1, cls=TCLink, bw=10)
        self.addLink(monitoring, s1, cls=TCLink, bw=10)
        self.addLink(server, s1, cls=TCLink, bw=10)


class TCPDumpCollector:
    def __init__(self, net, output_dir='tcpdump_data'):
        self.net = net
        self.output_dir = output_dir
        self.processes = {}
        os.makedirs(output_dir, exist_ok=True)

    def start_capture(self, node, interface=None, filter_str=None):
        try:
            if isinstance(node, str):
                node = self.net.get(node)

            if not node.waiting:
                if interface is None:
                    interfaces = [intf.name for intf in node.intfs.values() if intf.name != 'lo']
                else:
                    interfaces = [interface]

                for intf in interfaces:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f'{self.output_dir}/{node.name}_{intf}_{timestamp}.pcap'
                    cmd = ['tcpdump', '-i', intf, '-w', filename]
                    if filter_str:
                        cmd += [filter_str]

                    if node in self.net.hosts:
                        process = node.popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    else:
                        process = subprocess.Popen(
                            cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            preexec_fn=os.setsid
                        )

                    stderr_output = process.stderr.readline().decode().strip()
                    if stderr_output:
                        print(f"[tcpdump:{node.name}] {stderr_output}")

                    self.processes[(node.name, intf)] = {
                        'process': process,
                        'file': filename
                    }
                    print(f"Started tcpdump on {node.name} interface {intf}, saving to {filename}")

        except Exception as e:
            print(f"Error in start_capture for node {node}: {e}")

    def stop_capture(self, node=None, interface=None):
        try:
            if node:
                node_name = node if isinstance(node, str) else node.name
                to_stop = [(n, i) for n, i in self.processes.keys()
                           if n == node_name and (interface is None or i == interface)]
            else:
                to_stop = list(self.processes.keys())

            for node_name, intf in to_stop:
                try:
                    process_info = self.processes.pop((node_name, intf))
                    if 'process' in process_info:
                        os.killpg(os.getpgid(process_info['process'].pid), signal.SIGTERM)
                    print(f"Stopped tcpdump on {node_name} interface {intf}")
                except Exception as e:
                    print(f"Error stopping tcpdump on {node_name} interface {intf}: {e}")
        except Exception as e:
            print(f"Error in stop_capture: {e}")

    def cleanup(self):
        self.stop_capture()
        os.system('pkill -f tcpdump')
        print("Cleaned up all tcpdump processes")


# ---------- Embedded Server Function ----------
def start_dual_port_server(server_node, tcp_port=6000, udp_port=5555):
    server_code = f"""import socket, threading

TCP_HOST = '0.0.0.0'
TCP_PORT = {tcp_port}
UDP_HOST = '0.0.0.0'
UDP_PORT = {udp_port}

def handle_tcp_client(conn, addr):
    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
        conn.close()
    except Exception:
        conn.close()

def tcp_server():
    s_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s_tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s_tcp.bind((TCP_HOST, TCP_PORT))
    s_tcp.listen(5)
    while True:
        conn, addr = s_tcp.accept()
        threading.Thread(target=handle_tcp_client, args=(conn, addr), daemon=True).start()

def udp_server():
    s_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s_udp.bind((UDP_HOST, UDP_PORT))
    while True:
        data, addr = s_udp.recvfrom(1024)
        s_udp.sendto(b"ACK from UDP", addr)

threading.Thread(target=tcp_server, daemon=True).start()
threading.Thread(target=udp_server, daemon=True).start()
threading.Event().wait()
"""
    server_node.cmd('echo "{}" > /tmp/server_dual_ports.py'.format(server_code.replace('"', '\"')))
    server_node.cmd('python3 -u /tmp/server_dual_ports.py > server_log.txt 2>&1 &')
    print(f"[+] Dual-port TCP({tcp_port})/UDP({udp_port}) server started on {server_node.name}")


# ---------- Traffic Generators ----------
def generate_emergency_alerts(host, destination_ip, stop_event):
    while not stop_event.is_set():
        host.cmd(f'ping -c 1 -s 100 -Q 0x28 {destination_ip}')
        time.sleep(random.uniform(0.5, 2.0))


def generate_patient_monitoring_data(sender, destination_ip, stop_event):
    script_path = os.path.abspath('sensor_data_infinite.py')
    if not os.path.exists(script_path):
        print(f"Error: Cannot find {script_path}")
        return

    while not stop_event.is_set():
        sender.cmd(f'python3 -u {script_path} {destination_ip} > sender_log.txt 2>&1 &')
        time.sleep(random.uniform(0.2, 0.5))


def setup_netcat_listener(server):
    server.cmd('nc -lk 5001 > /dev/null &')


# ---------- Main ----------
def main():
    tcpdump_collector = None
    net = None
    threads = []
    stop_event = threading.Event()

    try:
        setLogLevel('info')
        os.system('mn -c')
        os.system('killall controller')
        os.system('pkill -f tcpdump')

        topo = customTopology()
        net = Mininet(topo=topo, switch=OVSSwitch, controller=Controller, link=TCLink, autoSetMacs=True)
        net.start()
        print("<<<<<<<<<<<<<<Waiting for network to initialize...>>>>>>>>>>>>>>>>")
        sleep(5)

        # Start packet capture
        tcpdump_collector = TCPDumpCollector(net)
        for switch in net.switches:
            tcpdump_collector.start_capture(switch)
        for host in net.hosts:
            tcpdump_collector.start_capture(host)

        # Start imaging listener (TCP 5001)
        setup_netcat_listener(net.get('server'))

        # Start dual-port server (TCP 6000, UDP 5555)
        start_dual_port_server(net.get('server'), tcp_port=tcp_port, udp_port=udp_port)

        # Start traffic generators
        thread_args = [
            (generate_emergency_alerts, 'emergency'),
            (generate_patient_monitoring_data, 'monitoring')
        ]
        for func, host_name in thread_args:
            thread = threading.Thread(
                target=func,
                args=(net.get(host_name), server_ip, stop_event)
            )
            thread.daemon = True
            threads.append(thread)
            thread.start()

        print("\n>>>>>>>>>>Network is ready. Press Ctrl+C to exit.<<<<<<<<<<<<")
        CLI(net)

    except KeyboardInterrupt:
        print("\n>>>>>>>>>>>>Shutting down network...<<<<<<<<<<<<<<")
    except Exception as e:
        print(f"Error in main: {e}")
    finally:
        stop_event.set()
        for thread in threads:
            thread.join(timeout=2)

        if tcpdump_collector:
            tcpdump_collector.cleanup()

        if net:
            net.stop()

        # Cleanup background processes
        os.system('pkill -f tcpdump')
        os.system('pkill -f "nc -lk"')
        os.system('pkill -f "python3 sensor_data_infinite.py"')
        os.system('pkill -f "/tmp/server_dual_ports.py"')

if __name__ == '__main__':
    main()
