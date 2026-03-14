#!/bin/bash
# pcap_to_csv_s5_v3.sh
# ============================================================
# Regenerates all_packets_extracted_s5.csv matching S1 exactly.
#
# S1 exact column order (16 cols):
#   frame.number, frame.time_epoch, frame.time_delta, frame.len,
#   ip.src, ip.dst, ip.proto,
#   tcp.srcport, tcp.dstport, tcp.len, tcp.flags,
#   mqtt.clientid, mqtt.topic, mqtt.qos, mqtt.msgtype, mqtt.msg
#
# Fixes vs previous version:
#   1. Removed ip.dsfield from header AND tshark fields
#   2. Column order matches S1 exactly
#   3. Header and tshark -e fields are now in sync
# ============================================================

PCAP_DIR="/home/ictlab7/Documents/Learning_Mininet/PcapForExpt"
OUTPUT_CSV="all_packets_extracted_s5.csv"
SCENARIO_TAG="s5"

# ── Find S5 pcap files ────────────────────────────────────────────────────────
PCAP_FILES=$(ls "${PCAP_DIR}"/*_${SCENARIO_TAG}_*.pcap 2>/dev/null)

if [ -z "$PCAP_FILES" ]; then
    echo "ERROR: No S5 pcap files found matching *_s5_*.pcap in ${PCAP_DIR}"
    echo "       Check actual filenames: ls ${PCAP_DIR}/"
    exit 1
fi

echo "Found S5 pcap files:"
echo "$PCAP_FILES" | while read f; do echo "  $(ls -lh $f | awk '{print $5, $9}')"; done
echo ""

# ── Choose single best source — NO looping over all files ────────────────────
# Looping over all 6 files causes 3–5× duplication (same packet seen on
# broker-eth0, s3-eth1, h13-eth0, s1-eth1, s1-eth2 simultaneously).
#
# Priority:
#   1. broker-eth0 — every MQTT packet in/out, no duplicates
#   2. s3-eth1     — all s3 traffic (backup if broker pcap is small)
#   3. first found (last resort)

BROKER_PCAP=$(ls "${PCAP_DIR}"/broker_*_${SCENARIO_TAG}_*.pcap 2>/dev/null | head -1)
S3_PCAP=$(ls "${PCAP_DIR}"/s3_s3-eth*_${SCENARIO_TAG}_*.pcap 2>/dev/null | head -1)

if [ -n "$BROKER_PCAP" ]; then
    PCAP_TO_USE="$BROKER_PCAP"
    echo "✅ Using broker-eth0 pcap (primary): $(basename $BROKER_PCAP)"
elif [ -n "$S3_PCAP" ]; then
    PCAP_TO_USE="$S3_PCAP"
    echo "⚠️  broker pcap not found. Using s3-eth: $(basename $S3_PCAP)"
else
    PCAP_TO_USE=$(echo "$PCAP_FILES" | grep -v '_lo_' | head -1)
    echo "⚠️  Fallback (non-loopback): $(basename $PCAP_TO_USE)"
fi
echo ""

# ── Write header — 16 columns, identical order to S1 ─────────────────────────
echo "frame.number,frame.time_epoch,frame.time_delta,frame.len,ip.src,ip.dst,ip.proto,tcp.srcport,tcp.dstport,tcp.len,tcp.flags,mqtt.clientid,mqtt.topic,mqtt.qos,mqtt.msgtype,mqtt.msg" \
    > "${OUTPUT_CSV}"

echo "Converting $(basename $PCAP_TO_USE) → CSV (16 fields, S1-identical order)..."

tshark -r "${PCAP_TO_USE}" \
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
    -E header=n \
    -E separator=, \
    -E quote=d \
    -E occurrence=f \
    2>/dev/null >> "${OUTPUT_CSV}"

ROWS=$(wc -l < "${OUTPUT_CSV}")
echo ""
echo "✅ Done: ${OUTPUT_CSV}"
echo "   Total rows (incl. header): ${ROWS}"

# ── Verify column match ───────────────────────────────────────────────────────
echo ""
echo "Verifying column match with S1..."
HEAD=$(head -1 "${OUTPUT_CSV}")
EXPECTED="frame.number,frame.time_epoch,frame.time_delta,frame.len,ip.src,ip.dst,ip.proto,tcp.srcport,tcp.dstport,tcp.len,tcp.flags,mqtt.clientid,mqtt.topic,mqtt.qos,mqtt.msgtype,mqtt.msg"

if [ "$HEAD" = "$EXPECTED" ]; then
    echo "✅ Columns match S1 exactly"
else
    echo "❌ Column mismatch!"
    echo "   Got:      $HEAD"
    echo "   Expected: $EXPECTED"
fi

echo ""
echo "Next: upload ${OUTPUT_CSV} to Google Drive, replace old S5 file, rerun preprocessor"
