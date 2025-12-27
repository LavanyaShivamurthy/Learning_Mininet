#!/bin/bash

# =====================================================
# FULL PCAP EXTRACTION + MQTT VALIDATION
# NO LABELING – ALL PACKETS INCLUDED
# =====================================================

if [ $# -ne 1 ]; then
    echo "Usage: $0 <pcap_file>"
    exit 1
fi

PCAP="$1"
OUT_DIR="csv_output"
CSV_FILE="$OUT_DIR/all_packets_extracted.csv"

mkdir -p "$OUT_DIR"

echo "=============================================="
echo " FULL PCAP EXTRACTION & MQTT VALIDATION"
echo " PCAP: $PCAP"
echo "=============================================="
echo

# -----------------------------------------------------
# 1. EXTRACT ALL PACKETS (MQTT FIELDS OPTIONAL)
# -----------------------------------------------------
echo "[1/6] Extracting ALL packets to CSV..."

tshark -r "$PCAP" \
  -T fields \
  -e frame.number \
  -e frame.time_epoch \
  -e frame.time_delta \
  -e frame.len \
  -e ip.src \
  -e ip.dst \
  -e ip.proto \
  -e tcp.srcport \
  -e tcp.dstport \
  -e tcp.len \
  -e tcp.flags \
  -e mqtt.clientid \
  -e mqtt.topic \
  -e mqtt.qos \
  -e mqtt.msgtype \
  -e mqtt.msg \
  -E header=y \
  -E separator=, \
  -E quote=d \
  -E occurrence=f \
  > "$CSV_FILE"

echo "✔ CSV created: $CSV_FILE"
echo "Total rows:"
wc -l "$CSV_FILE"
echo

# -----------------------------------------------------
# 2. MQTT TOPIC PRESENCE & CORRECTNESS
# -----------------------------------------------------
echo "[2/6] MQTT TOPIC DISTRIBUTION"
echo "-----------------------------"

cut -d',' -f13 "$CSV_FILE" | tail -n +2 | grep -v '^$' | sort | uniq -c
echo

echo "Topic hierarchy depth:"
cut -d',' -f13 "$CSV_FILE" | tail -n +2 | grep -v '^$' | awk -F'/' '{print NF}' | sort | uniq -c
echo

# -----------------------------------------------------
# 3. MQTT QoS DISTRIBUTION
# -----------------------------------------------------
echo "[3/6] MQTT QoS DISTRIBUTION"
echo "--------------------------"

cut -d',' -f14 "$CSV_FILE" | tail -n +2 | grep -v '^$' | sort | uniq -c
echo

# -----------------------------------------------------
# 4. ADMIN vs SENSOR TRAFFIC CHECK
# -----------------------------------------------------
echo "[4/6] ADMIN vs SENSOR TRAFFIC"
echo "------------------------------"

echo "Admin topics:"
grep ",admin/" "$CSV_FILE" | cut -d',' -f13 | sort | uniq -c
echo

echo "Sensor topics:"
grep ",sensors/" "$CSV_FILE" | cut -d',' -f13 | sort | uniq -c
echo

# -----------------------------------------------------
# 5. PAYLOAD SANITY (NO LABEL LEAKAGE)
# -----------------------------------------------------
echo "[5/6] PAYLOAD SANITY CHECK"
echo "--------------------------"

if grep -Ei "class=|emergency|important" "$CSV_FILE" > /dev/null; then
    echo "✖ WARNING: Label-like text found in payload"
    grep -Ei "class=|emergency|important" "$CSV_FILE" | head
else
    echo "✔ OK: No labels embedded in payload"
fi
echo

# -----------------------------------------------------
# 6. INTER-ARRIVAL TIME ANALYSIS (frame.time_delta)
# -----------------------------------------------------
echo "[6/6] INTER-ARRIVAL TIME (AVG PER TOPIC)"
echo "----------------------------------------"

awk -F',' '
NR>1 && $13!="" {
    topic=$13
    delta=$3
    sum[topic]+=delta
    count[topic]++
}
END {
    for (t in sum)
        printf "%-35s %.4f sec\n", t, sum[t]/count[t]
}' "$CSV_FILE"
echo

echo "=============================================="
echo " EXTRACTION & VALIDATION COMPLETE"
echo "=============================================="

