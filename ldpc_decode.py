#!/usr/bin/env python3
import numpy as np
import sys
import argparse
from pyldpc import make_ldpc

# --- DEFAULT PARAMETERS (must match encoder) ---
N = 1024  
D_V = 3   
D_C = 16
SEED = 12345
# -----------------------------------------------

def generate_ldpc_params(n, d_v, d_c, seed):
    """Generates LDPC parameters deterministically - must match encoder."""
    print(f"Generating LDPC matrices with n={n}, d_v={d_v}, d_c={d_c}, seed={seed}...", file=sys.stderr)
    
    np.random.seed(seed)
    
    try:
        H, G = make_ldpc(n, d_v, d_c, systematic=True, sparse=True)
        H_dense = H.toarray() if hasattr(H, "toarray") else H
        G_dense = G.toarray() if hasattr(G, "toarray") else G
        
        if G_dense.shape[0] > G_dense.shape[1]:
            G_dense = G_dense.T
        
        k = G_dense.shape[0]
        
        print(f"Generated LDPC({n},{k}) code for decoding", file=sys.stderr)
        print(f"  Code rate: {k/n:.4f}", file=sys.stderr)
        
        return H_dense, k, n
    except Exception as e:
        print(f"Error generating LDPC matrices: {e}", file=sys.stderr)
        sys.exit(1)


def estimate_snr_from_iats(iat_values, threshold):
    """Estimate SNR from IAT measurements."""
    low_iats = [iat for iat in iat_values if iat < threshold]
    high_iats = [iat for iat in iat_values if iat > threshold]
    
    if len(low_iats) == 0 or len(high_iats) == 0:
        print("Warning: All IATs on one side of threshold, using default SNR=15dB", file=sys.stderr)
        return 15.0
    
    mean_low = np.mean(low_iats)
    mean_high = np.mean(high_iats)
    signal_separation = abs(mean_high - mean_low)
    
    std_low = np.std(low_iats) if len(low_iats) > 1 else 0.001
    std_high = np.std(high_iats) if len(high_iats) > 1 else 0.001
    avg_noise = (std_low + std_high) / 2
    
    if avg_noise < 1e-6:
        snr_linear = 1000
    else:
        snr_linear = signal_separation / avg_noise
    
    snr_db = 10 * np.log10(snr_linear) if snr_linear > 0 else 0
    snr_db = np.clip(snr_db, 0, 30)
    
    print(f"\n=== Channel Estimation ===", file=sys.stderr)
    print(f"  Low IAT: mean={mean_low:.4f}, std={std_low:.6f} ({len(low_iats)} samples)", file=sys.stderr)
    print(f"  High IAT: mean={mean_high:.4f}, std={std_high:.6f} ({len(high_iats)} samples)", file=sys.stderr)
    print(f"  Signal separation: {signal_separation:.4f}", file=sys.stderr)
    print(f"  Average noise: {avg_noise:.6f}", file=sys.stderr)
    print(f"  Estimated SNR: {snr_db:.2f} dB", file=sys.stderr)
    print(f"=========================\n", file=sys.stderr)
    
    return snr_db


def iats_to_llr(iat_values, threshold, snr_db):
    """Converts IAT values to Log-Likelihood Ratios (LLR)."""
    snr_linear = 10 ** (snr_db / 10.0)
    
    llr_values = []
    for iat in iat_values:
        deviation = iat - threshold
        llr = deviation * snr_linear
        llr_values.append(llr)
    
    llr_array = np.array(llr_values, dtype=float)
    hard_bits = np.array([1 if iat <= threshold else 0 for iat in iat_values], dtype=np.uint8)
    
    print(f"Converted {len(iat_values)} IATs to LLR values (SNR={snr_db:.2f}dB)", file=sys.stderr)
    print(f"  LLR range: [{np.min(llr_array):.3f}, {np.max(llr_array):.3f}]", file=sys.stderr)
    print(f"  Hard decision: {np.sum(hard_bits)} ones, {len(hard_bits) - np.sum(hard_bits)} zeros", file=sys.stderr)
    
    return llr_array, hard_bits


def decode_sum_product(H, llr_ch, max_iter=50, damping=0.75):
    """Sum-Product Algorithm (Belief Propagation) for LDPC decoding."""
    m, n = H.shape
    
    L_v2c = np.zeros((m, n), dtype=float)
    L_c2v = np.zeros((m, n), dtype=float)
    
    for i in range(m):
        for j in range(n):
            if H[i, j] == 1:
                L_v2c[i, j] = llr_ch[j]
    
    for iteration in range(max_iter):
        L_c2v_new = np.zeros((m, n), dtype=float)
        
        for i in range(m):
            connected_vars = np.where(H[i, :] == 1)[0]
            
            for j in connected_vars:
                other_vars = connected_vars[connected_vars != j]
                
                if len(other_vars) == 0:
                    L_c2v_new[i, j] = 0
                else:
                    sign_product = np.prod(np.sign(L_v2c[i, other_vars]))
                    abs_vals = np.abs(L_v2c[i, other_vars])
                    magnitude = np.min(abs_vals)
                    L_c2v_new[i, j] = sign_product * magnitude
        
        L_c2v = damping * L_c2v_new + (1 - damping) * L_c2v
        
        L_v2c_new = np.zeros((m, n), dtype=float)
        L_total = np.copy(llr_ch)
        
        for j in range(n):
            connected_checks = np.where(H[:, j] == 1)[0]
            
            for i in connected_checks:
                L_total[j] += L_c2v[i, j]
            
            for i in connected_checks:
                L_v2c_new[i, j] = L_total[j] - L_c2v[i, j]
        
        L_v2c = L_v2c_new
        
        decoded = (L_total < 0).astype(np.uint8)
        
        syndrome = np.mod(H @ decoded, 2)
        
        if not np.any(syndrome):
            print(f"  Sum-Product converged at iteration {iteration + 1}", file=sys.stderr)
            return decoded
    
    print(f"  Sum-Product: Max iterations ({max_iter}) reached", file=sys.stderr)
    print(f"  Warning: Syndrome still has {np.sum(syndrome)} unsatisfied checks", file=sys.stderr)
    return (L_total < 0).astype(np.uint8)


def decode_ldpc_pipeline(iats, H, k, n, threshold, snr_db):
    """Full decoding pipeline."""
    decoded_message_bits = []
    
    llr_values, hard_bits = iats_to_llr(iats, threshold, snr_db)
    
    num_blocks = len(llr_values) // n
    print(f"\nDecoding {num_blocks} blocks using Sum-Product Algorithm...", file=sys.stderr)

    for i in range(num_blocks):
        print(f"\nBlock {i+1}/{num_blocks}:", file=sys.stderr)
        start, end = i * n, (i + 1) * n
        
        llr_block = llr_values[start:end]
        decoded_codeword = decode_sum_product(H, llr_block, max_iter=50, damping=0.75)
        message_block = decoded_codeword[:k]
        decoded_message_bits.append(message_block)

    if not decoded_message_bits:
        return None
    
    return np.concatenate(decoded_message_bits)


def bits_to_bytes(bits):
    """Converts a numpy array of bits (LSB-first) to a byte string."""
    remainder = len(bits) % 8
    if remainder != 0:
        bits = np.pad(bits, (0, 8 - remainder), 'constant')
    return np.packbits(bits, bitorder='little').tobytes()


def main():
    parser = argparse.ArgumentParser(
        description="LDPC Sum-Product (Belief Propagation) decoder for IAT covert channels.",
        epilog="Example: %(prog)s times.csv 0.15 --seed 12345 --orig-len 800"
    )
    parser.add_argument("input_iat_file", help="File containing IAT values")
    parser.add_argument("threshold", type=float, help="Threshold for bit detection")
    parser.add_argument('-N', type=int, default=N, help=f"Codeword length (default: {N})")
    parser.add_argument('-dv', type=int, default=D_V, help=f"Variable node degree (default: {D_V})")
    parser.add_argument('-dc', type=int, default=D_C, help=f"Check node degree (default: {D_C})")
    parser.add_argument('--seed', type=int, default=SEED, help=f"Seed (default: {SEED})")
    parser.add_argument('--orig-len', type=int, required=True, help="Original message bit length")
    parser.add_argument('--snr', type=float, default=None, help="SNR in dB (auto-estimated if not provided)")
    args = parser.parse_args()

    print("="*60, file=sys.stderr)
    print("LDPC Sum-Product (Belief Propagation) Decoder", file=sys.stderr)
    print("="*60, file=sys.stderr)
    
    H, k, n = generate_ldpc_params(args.N, args.dv, args.dc, args.seed)

    try:
        with open(args.input_iat_file, 'r') as f:
            content = f.read().replace('\n', ',')
        iat_values = [float(val) for val in content.split(',') if val.strip()]
        print(f"\nRead {len(iat_values)} IAT values from {args.input_iat_file}", file=sys.stderr)
        print(f"  IAT range: [{min(iat_values):.3f}, {max(iat_values):.3f}]", file=sys.stderr)
        print(f"  Threshold: {args.threshold:.3f}", file=sys.stderr)
    except Exception as e:
        print(f"Error reading IAT file: {e}", file=sys.stderr)
        sys.exit(1)

    # THIS IS THE KEY SECTION
    if args.snr is None:
        snr_db = estimate_snr_from_iats(iat_values, args.threshold)
        print(f">>> Using AUTO-ESTIMATED SNR: {snr_db:.2f} dB <<<", file=sys.stderr)
    else:
        snr_db = args.snr
        print(f">>> Using PROVIDED SNR: {snr_db:.2f} dB <<<", file=sys.stderr)

    concatenated_message_bits = decode_ldpc_pipeline(iat_values, H, k, n, args.threshold, snr_db)

    if concatenated_message_bits is None:
        print("\nError: Decoding failed.", file=sys.stderr)
        sys.exit(1)

    final_bits = concatenated_message_bits[:args.orig_len]
    print(f"\nDecoded and truncated to {args.orig_len} message bits.", file=sys.stderr)

    final_bytes = bits_to_bytes(final_bits)
    sys.stdout.buffer.write(final_bytes)
    
    print(f"\n" + "="*60, file=sys.stderr)
    print(f"Decoding complete! Wrote {len(final_bytes)} bytes to stdout.", file=sys.stderr)
    print(f"="*60, file=sys.stderr)


if __name__ == "__main__":
    main()