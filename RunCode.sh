#!/bin/bash

#  Code Change V1 :
    # 1.  Added Contl+c handler
    # 2 . BaseCode_Mqtt_collector.py Run in foreground instead of background
    # Working fine
set -Eeuo pipefail

cleanup() {
    echo
    echo "🛑 Ctrl+C detected — cleaning up safely..."

    sudo pkill -f tcpdump || true
    sudo pkill -f mosquitto || true
    sudo pkill -f mnexec || true
    sudo mn -c >/dev/null 2>&1 || true

    # Remove OVS bridges safely
    for br in $(sudo ovs-vsctl list-br); do
        sudo ovs-vsctl del-br "$br" || true
    done

    echo "✅ Cleanup complete. Exiting."
    exit 0
}

# Trap Ctrl+C and termination signals
trap cleanup SIGINT SIGTERM

echo "-----------------------------------------------------------"
echo "🔹 Checking and Starting Open vSwitch service..."
echo "-----------------------------------------------------------"

if [ ! -f /etc/openvswitch/conf.db ]; then
    echo "⚠️ OVS database not found. Recreating..."
    sudo ovsdb-tool create /etc/openvswitch/conf.db \
        /usr/share/openvswitch/vswitch.ovsschema
fi

sudo /usr/share/openvswitch/scripts/ovs-ctl stop >/dev/null 2>&1 || true
sudo /usr/share/openvswitch/scripts/ovs-ctl start

if sudo ovs-vsctl show >/dev/null 2>&1; then
    echo "✅ Open vSwitch is running properly."
else
    echo "❌ Open vSwitch failed to start."
    exit 1
fi

echo "-----------------------------------------------------------"
echo "🧹 Cleaning up previous Mininet sessions..."
echo "-----------------------------------------------------------"

sudo mn -c >/dev/null 2>&1 || true

# Remove stale interfaces
for iface in $(ip link show | grep -o '[-_.[:alnum:]]\+-eth[0-9]\+'); do
    sudo ip link delete "$iface" 2>/dev/null || true
done

echo "✅ Mininet cleanup complete."
echo "-----------------------------------------------------------"

echo "🚀 Starting Mininet simulation..."
echo "-----------------------------------------------------------"

# Run Mininet/controller (FOREGROUND, no &)
python3 BaseCode_Mqtt_Collector.py
