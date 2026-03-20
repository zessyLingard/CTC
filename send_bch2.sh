#!/bin/bash

EXP_NAME="vpn_fuzzy_usa"
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
    iat_fuzzy="iat_fuzzy.txt"
    timing_file="$TIMING_DIR/${fname}.txt"

    echo "[SEND] $fname"

    # BCH timing encode (500 / 1000 ms)
    ./bch_encode "$file" 500 1000 > "$iat_file"

    # Apply fuzzy/jitter
    python3 script.py "$iat_file" 500 > "$iat_fuzzy"

    # Save timings (optional, for analysis)
    python3 convert.py "$iat_fuzzy" "$timing_file" >/dev/null 2>&1

    # Send covert channel (FUZZY timings)
    ./client -D "$SERVER_IP" -P "$PORT" -f "$iat_fuzzy"

    sleep 5
done

END_TIME=$(date +%s.%N)
TOTAL_TIME=$(echo "$END_TIME - $START_TIME" | bc)

echo "[TIME] Total transmission time: ${TOTAL_TIME}s"

