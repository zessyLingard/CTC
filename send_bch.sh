#!/bin/bash

EXP_NAME="vpn_no_fuzzy"
SERVER_IP="222.252.10.124"
PORT=3334

PART_DIR="data"
TIMING_DIR="timings_$EXP_NAME"

mkdir -p "$TIMING_DIR"

echo "Starting transmission..."
START_TIME=$(date +%s.%N)

for file in "$PART_DIR"/part_*; do
    fname=$(basename "$file")
    iat_file="iat_manual.txt"
    timing_file="$TIMING_DIR/${fname}.txt"

    echo "[SEND] $fname"

    ./bch_encode "$file" 500 1000 > "$iat_file"
    python3 convert.py "$iat_file" "$timing_file" >/dev/null 2>&1
    ./client -D "$SERVER_IP" -P "$PORT" -f "$iat_file"

    sleep 5
done

END_TIME=$(date +%s.%N)

TOTAL_TIME=$(echo "$END_TIME - $START_TIME" | bc)
echo "[TIME] Total transmission time: ${TOTAL_TIME}s"

