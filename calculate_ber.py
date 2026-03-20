import sys

if len(sys.argv) < 2:
    print("Usage: python calculate_ber.py <threshold>")
    sys.exit(1)

threshold = float(sys.argv[1])

log_file = "timing.txt"    # Received IAT (after network)
out_file = "output.txt"    # Original IAT (before network)

# Read values
with open(log_file) as f:
    recv_vals = [float(x.strip()) for x in f if x.strip()]

with open(out_file) as f:
    orig_vals = [float(x.strip()) for x in f if x.strip()]

# Ensure same length
length = min(len(recv_vals), len(orig_vals))

# Convert to bits and compare
bit_errors = 0
errors = []

for i in range(length):
    orig_bit = 1 if orig_vals[i] <= threshold else 0
    recv_bit = 1 if recv_vals[i] <= threshold else 0
    
    if orig_bit != recv_bit:
        bit_errors += 1
        errors.append({
            'line': i + 1,  # 1-indexed line number
            'orig_val': orig_vals[i],
            'recv_val': recv_vals[i],
            'orig_bit': orig_bit,
            'recv_bit': recv_bit
        })

ber = bit_errors / length if length > 0 else 0

# Print results
print(f"=== BER Analysis ===")
print(f"Threshold: {threshold}")
print(f"Total bits: {length}")
print(f"Bit errors: {bit_errors}")
print(f"BER: {ber:.6f} ({ber*100:.4f}%)")
print()

if errors:
    print("Error positions (line numbers):")
    print("-" * 60)
    for e in errors:
        print(f"Line {e['line']:4d}: sent {e['orig_bit']} ({e['orig_val']:.6f}) → recv {e['recv_bit']} ({e['recv_val']:.6f})")
else:
    print("✓ No bit errors detected!")