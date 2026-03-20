#!/usr/bin/env python3

import os
import sys
import csv

if len(sys.argv) != 4:
    print(f"Usage: {sys.argv[0]} <threshold_seconds> <tx_folder> <rx_folder>")
    print(f"Example: {sys.argv[0]} 0.15 timings_part timings_no_vpn")
    sys.exit(1)

# Threshold is GIVEN directly in seconds
threshold = float(sys.argv[1])
tx_dir = sys.argv[2]
rx_dir = sys.argv[3]

print("=== BER ANALYSIS (THRESHOLD IN SECONDS) ===")
print(f"threshold : {threshold:.6f} s")
print(f"TX folder : {tx_dir}")
print(f"RX folder : {rx_dir}")
print()

total_bits = 0
total_errors = 0
summary_rows = []
error_log = []

for tx_name in sorted(os.listdir(tx_dir)):
    if not tx_name.startswith("part_") or not tx_name.endswith(".txt"):
        continue

    suffix = tx_name[5:-4]  # aa, ab, ...
    tx_path = os.path.join(tx_dir, tx_name)
    rx_path = os.path.join(rx_dir, f"log_{suffix}.txt")

    print(f"[DEBUG] Comparing:")
    print(f"        TX: {tx_path}")
    print(f"        RX: {rx_path}")

    if not os.path.isfile(rx_path):
        print(f"[WARN] RX file missing, skipping part_{suffix}")
        continue

    with open(tx_path) as f:
        tx_vals = [float(x.strip()) for x in f if x.strip()]

    with open(rx_path) as f:
        rx_vals = [float(x.strip()) for x in f if x.strip()]

    print(f"[DEBUG] TX values (first 5): {tx_vals[:5]}")
    print(f"[DEBUG] RX values (first 5): {rx_vals[:5]}")

    length = min(len(tx_vals), len(rx_vals))
    errors = 0
    part_error_lines = []

    print(f"[CHECK part_{suffix}] (first {min(10, length)} bits)")
    for i in range(min(10, length)):
        tx_bit = 1 if tx_vals[i] < threshold else 0
        rx_bit = 1 if rx_vals[i] < threshold else 0
        print(
            f"  i={i+1:2d} "
            f"TX={tx_vals[i]:.6f}({tx_bit}) "
            f"RX={rx_vals[i]:.6f}({rx_bit})"
        )

    for i in range(length):
        tx_bit = 1 if tx_vals[i] < threshold else 0
        rx_bit = 1 if rx_vals[i] < threshold else 0

        if tx_bit != rx_bit:
            errors += 1
            part_error_lines.append(
                f"  bit {i+1:4d}: "
                f"TX={tx_bit} ({tx_vals[i]:.6f}) "
                f"RX={rx_bit} ({rx_vals[i]:.6f})"
            )

    ber = errors / length if length else 0.0

    print(f"[RESULT part_{suffix}] bits={length} errors={errors} BER={ber:.6e}\n")

    summary_rows.append([
        f"part_{suffix}",
        length,
        errors,
        ber
    ])

    total_bits += length
    total_errors += errors

    if part_error_lines:
        error_log.append(f"part_{suffix}:")
        error_log.extend(part_error_lines)
        error_log.append("")

# Totals
total_ber = total_errors / total_bits if total_bits else 0.0
summary_rows.append(["TOTAL", total_bits, total_errors, total_ber])

print("=== TOTAL ===")
print(f"Total bits  : {total_bits}")
print(f"Bit errors : {total_errors}")
print(f"BER        : {total_ber:.6e}")

# Write CSV
with open("ber_report.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["message", "bits", "errors", "ber"])
    writer.writerows(summary_rows)

# Write error positions
with open("bit_errors.txt", "w") as f:
    f.write("\n".join(error_log) if error_log else "No bit errors detected\n")

print("\nOutputs:")
print("  - ber_report.csv")
print("  - bit_errors.txt")
