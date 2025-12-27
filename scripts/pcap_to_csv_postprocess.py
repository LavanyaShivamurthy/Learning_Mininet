import sys
import pandas as pd
import os

if len(sys.argv) < 2:
    print("Usage: python3 pcap_to_csv_postprocess.py <csv_file>")
    sys.exit(1)

csv_file = sys.argv[1]
print(f"🧹 Cleaning CSV: {csv_file}")

try:
    df = pd.read_csv(csv_file)
    # Drop mqtt.msg if present
    if "mqtt.msg" in df.columns:
        df.drop(columns=["mqtt.msg"], inplace=True)
    # Fill empty cells with NaN for Excel readability
    df = df.fillna("")
    df.to_csv(csv_file, index=False)
    print(f"✅ Cleaned and saved: {csv_file}")
except Exception as e:
    print(f"❌ Error: {e}")

