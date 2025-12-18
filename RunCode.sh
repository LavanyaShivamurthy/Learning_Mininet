#!/bin/bash
set -e  # Exit immediately if a command fails

echo "-----------------------------------------------------------"
echo "🔹 Checking and Starting Open vSwitch service..."
echo "-----------------------------------------------------------"

# Check if OVS DB exists, recreate if missing
if [ ! -f /etc/openvswitch/conf.db ]; then
  echo "⚠️ OVS database not found. Recreating..."
  sudo ovsdb-tool create /etc/openvswitch/conf.db /usr/share/openvswitch/vswitch.ovsschema
fi

# Stop any stale OVS instances
sudo /usr/share/openvswitch/scripts/ovs-ctl stop > /dev/null 2>&1 || true

# Start OVS cleanly
sudo /usr/share/openvswitch/scripts/ovs-ctl start

# Verify OVS is active
if sudo ovs-vsctl show > /dev/null 2>&1; then
  echo "✅ Open vSwitch is running properly.\n"
else
  echo "❌ Open vSwitch failed to start. Please check logs with: journalctl -u openvswitch-switch\n"
  exit 1
fi

echo "-----------------------------------------------------------"
echo "🧹 Cleaning up previous Mininet sessions..."
echo "-----------------------------------------------------------"

# Full Mininet cleanup
sudo mn -c > /dev/null 2>&1
sudo pkill -9 -f "mnexec" > /dev/null 2>&1 || true
sudo pkill -9 -f "mininet:" > /dev/null 2>&1 || true
sudo pkill -9 -f "Tunnel=Ethernet" > /dev/null 2>&1 || true
sudo pkill -9 -f "controller" > /dev/null 2>&1 || true
sudo pkill -9 -f "ovs-testcontroller" > /dev/null 2>&1 || true
sudo pkill -9 -f "mosquitto" > /dev/null 2>&1 || true
sudo pkill -9 -f "tcpdump" > /dev/null 2>&1 || true
sudo pkill -9 -f "python3" > /dev/null 2>&1 || true
sudo rm -f /tmp/vconn* /tmp/vlogs* /tmp/*.out /tmp/*.log
sudo rm -f ~/.ssh/mn/* > /dev/null 2>&1 || true

# Remove old links
for iface in $(ip link show | egrep -o '([-_.[:alnum:]]+-eth[[:digit:]]+)'); do
  sudo ip link delete "$iface" 2>/dev/null || true
done

# Verify OVS bridges are gone
sudo ovs-vsctl list-br | while read -r br; do
  echo "⚠️ Removing old bridge: $br \n"
  sudo ovs-vsctl del-br "$br"
done

echo "✅ Mininet cleanup complete.\n"
echo "-----------------------------------------------------------"

# Optional pause before launching the experiment
sleep 1

echo "\n🚀 Starting Mininet simulation...\n"
echo "-----------------------------------------------------------"

# Run your main topology script
stdbuf -oL python3 BaseCode_Mqtt_Collector.py 2>&1 | tee BaseCode_Run.log

#python3 BaseCode_Mqtt_Collector.py
