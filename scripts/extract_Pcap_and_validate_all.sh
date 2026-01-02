# =====================================================
# FULL PCAP EXTRACTION + MQTT VALIDATION
# LOCAL → VALIDATE → APPEND
# =====================================================

if [ $# -ne 2 ]; then
    echo "Usage: $0 <pcap_file> <experiment_seed>"
    exit 1
fi

PCAP="$1"
EXPERIMENT_SEED="$2"

OUT_DIR="csv_output"
GLOBAL_CSV="$OUT_DIR/all_packets_extracted.csv"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOCAL_CSV="$OUT_DIR/extract_${EXPERIMENT_SEED}_${TIMESTAMP}.csv"

mkdir -p "$OUT_DIR"

echo "=============================================="
echo " FULL PCAP EXTRACTION & MQTT VALIDATION"
echo " PCAP      : $PCAP"
echo " SEED      : $EXPERIMENT_SEED"
echo " LOCAL CSV : $LOCAL_CSV"
echo "=============================================="
echo

# -----------------------------------------------------
# 1. EXTRACT ALL PACKETS → LOCAL CSV ONLY
# -----------------------------------------------------
echo "[1/6] Extracting ALL packets to LOCAL CSV..."

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
  > "$LOCAL_CSV"

echo "✔ Local CSV created: $LOCAL_CSV"
wc -l "$LOCAL_CSV"
echo

# -----------------------------------------------------
# 2. MQTT TOPIC PRESENCE & CORRECTNESS (LOCAL)
# -----------------------------------------------------
echo "[2/6] MQTT TOPIC DISTRIBUTION (LOCAL)"
echo "------------------------------------"

cut -d',' -f13 "$LOCAL_CSV" | tail -n +2 | grep -v '^$' | sort | uniq -c
echo

echo "Topic hierarchy depth:"
cut -d',' -f13 "$LOCAL_CSV" | tail -n +2 | grep -v '^$' | awk -F'/' '{print NF}' | sort | uniq -c
echo

# -----------------------------------------------------
# 3. MQTT QoS DISTRIBUTION (LOCAL)
# -----------------------------------------------------
echo "[3/6] MQTT QoS DISTRIBUTION (LOCAL)"
echo "----------------------------------"

cut -d',' -f14 "$LOCAL_CSV" | tail -n +2 | grep -v '^$' | sort | uniq -c
echo

# -----------------------------------------------------
# 4. ADMIN vs SENSOR TRAFFIC (LOCAL)
# -----------------------------------------------------
echo "[4/6] ADMIN vs SENSOR TRAFFIC (LOCAL)"
echo "------------------------------------"

echo "Admin topics:"
grep ",admin/" "$LOCAL_CSV" | cut -d',' -f13 | sort | uniq -c
echo

echo "Sensor topics:"
grep ",sensor/" "$LOCAL_CSV" | cut -d',' -f13 | sort | uniq -c
echo

# -----------------------------------------------------
# 5. PAYLOAD SANITY CHECK (LOCAL)
# -----------------------------------------------------
echo "[5/6] PAYLOAD SANITY CHECK (LOCAL)"
echo "---------------------------------"

if grep -Ei "class=|emergency|important" "$LOCAL_CSV" > /dev/null; then
    echo "✖ WARNING: Label-like text found in payload"
    grep -Ei "class=|emergency|important" "$LOCAL_CSV" | head
else
    echo "✔ OK: No labels embedded in payload"
fi
echo

# -----------------------------------------------------
# 6. INTER-ARRIVAL TIME (LOCAL)
# -----------------------------------------------------
echo "[6/6] INTER-ARRIVAL TIME (AVG PER TOPIC)"
echo "---------------------------------------"

awk -F',' '
NR>1 && $13!="" {
    topic = $13
    time  = $2   # frame.time_epoch

    if (prev_time[topic] != "") {
        delta = time - prev_time[topic]
        sum[topic] += delta
        count[topic]++
    }

    prev_time[topic] = time
}
END {
    for (t in sum)
        printf "%-35s %.4f sec\n", t, sum[t]/count[t]
}' "$CSV_FILE"




# -----------------------------------------------------
# 7. APPEND LOCAL → GLOBAL (SAFE)
# -----------------------------------------------------
echo "[FINAL] Appending LOCAL CSV to GLOBAL CSV..."

if [ ! -f "$GLOBAL_CSV" ]; then
    cp "$LOCAL_CSV" "$GLOBAL_CSV"
else
    tail -n +2 "$LOCAL_CSV" >> "$GLOBAL_CSV"
fi

echo "✔ Appended to: $GLOBAL_CSV"
echo "Total GLOBAL rows:"
wc -l "$GLOBAL_CSV"

echo
echo "=============================================="
echo " EXTRACTION, VALIDATION & APPEND COMPLETE"
echo "=============================================="

