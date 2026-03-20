#!/bin/bash

SERVER_IP="222.252.10.124"
PORT=3334

for file in data/part_*; do
    fname=$(basename "$file")
    echo "[CLIENT] Sending $fname ..."

    # Encode using LDPC
    python3 ldpc_encode.py "$file" 100 200 > iat_manual.txt

    # Add noise
    python3 script.py iat_manual.txt 100 > iat_fuzzy.txt

    # Send
    ./client -D "$SERVER_IP" -P "$PORT" -f iat_fuzzy.txt

    echo "[CLIENT] Sent $fname ✓"
    sleep 10
done

echo "[CLIENT] All parts sent!"
