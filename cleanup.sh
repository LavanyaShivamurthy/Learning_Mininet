# 1️⃣ Kill all leftover Mininet and OVS processes
sudo pkill -f mininet
sudo pkill -f controller
sudo pkill -f ovs-vswitchd
sudo pkill -f ovsdb-server

# 2️⃣ Delete all OVS bridges
for br in $(sudo ovs-vsctl list-br); do
    sudo ovs-vsctl del-br $br
done

# 3️⃣ Remove any leftover kernel datapaths
for dp in $(ip link show | grep -o 'dp[0-9]\+'); do
    sudo ip link delete $dp
done

# 4️⃣ Clean temporary Mininet files and SSH tunnels
sudo rm -f /tmp/vconn* /tmp/vlogs* /tmp/*.out /tmp/*.log
rm -rf ~/.ssh/mn/*

# 5️⃣ Verify cleanup
sudo ovs-vsctl list-br        # should show no bridges
ip link show | grep dp        # should show nothing

