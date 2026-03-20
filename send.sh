#!/bin/bash

SERVER_IP="222.252.10.124"
PORT=3334
PART_DIR="data"

echo "Starting transmission..."
START_TIME=$(date +%s.%N)

for file in "$PART_DIR"/part_*; do
    fname=$(basename "$file")
    iat_file="iat_manual.txt"
    iat_fuzzy="iat_fuzzy.txt"

    echo "[SEND] $fname"

    ./iat_encode "$file" 500 1000 > "$iat_file"

    python3 script.py "$iat_file" 500 > "$iat_fuzzy"
    #  Send directly
    ./client -D "$SERVER_IP" -P "$PORT" -f "$iat_file"

    sleep 5
done

END_TIME=$(date +%s.%N)
TOTAL_TIME=$(echo "$END_TIME - $START_TIME" | bc)

echo "[TIME] Total transmission time: ${TOTAL_TIME}s"
