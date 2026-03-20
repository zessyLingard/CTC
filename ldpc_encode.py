#!/usr/bin/env python3
import numpy as np
import sys
import argparse
from pyldpc import make_ldpc

# --- PARAMETERS FOR LDPC (1024, ~834) ---
N = 1024  
D_V = 3   
D_C = 16  
SEED = 12345  # Default seed for deterministic generation
# -----------------------------------------

def generate_ldpc_matrices(n, d_v, d_c, seed):
    """Generates LDPC H and G matrices deterministically."""
    print(f"Generating LDPC matrices with n={n}, d_v={d_v}, d_c={d_c}, seed={seed}...", file=sys.stderr)
    
    # Set seed for deterministic generation
    np.random.seed(seed)
    
    try:
        # Generate systematic LDPC code
        H, G = make_ldpc(n, d_v, d_c, systematic=True, sparse=True)
        
        # Convert to dense arrays for easier manipulation
        H_dense = H.toarray() if hasattr(H, "toarray") else H
        G_dense = G.toarray() if hasattr(G, "toarray") else G
        
        # Determine k (message length) from the generator matrix
        if G_dense.shape[0] > G_dense.shape[1]:
            G_dense = G_dense.T
        
        k = G_dense.shape[0]
        
        print(f"Generated LDPC({n},{k}) code:", file=sys.stderr)
        print(f"  Code rate: {k/n:.4f}", file=sys.stderr)
        
        return H_dense, G_dense, k
        
    except Exception as e:
        print(f"Error generating LDPC matrices: {e}", file=sys.stderr)
        sys.exit(1)


def file_to_bits(filename):
    """Read a file and convert to bit array (LSB-first)."""
    try:
        with open(filename, 'rb') as f:
            file_bytes = f.read()
        
        # Convert bytes to bits, ensuring LSB-first order for consistency
        bits = np.unpackbits(np.frombuffer(file_bytes, dtype=np.uint8), bitorder='little')
        print(f"Read {len(file_bytes)} bytes ({len(bits)} bits) from {filename}", file=sys.stderr)
        
        return bits
    except Exception as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(1)


def pad_to_block_size(bits, block_size):
    """Pad bit array to a multiple of block_size."""
    remainder = len(bits) % block_size
    if remainder == 0:
        return bits
    
    padding_len = block_size - remainder
    padded_bits = np.concatenate((bits, np.zeros(padding_len, dtype=np.uint8)))
    print(f"Padded {len(bits)} bits to {len(padded_bits)} bits", file=sys.stderr)
    return padded_bits


def encode_ldpc_correct(bits, G, k, H, n):
    padded_bits = pad_to_block_size(bits, k)
    num_blocks = len(padded_bits) // k
    encoded_blocks = []

    print(f"Encoding {num_blocks} blocks of length {k} each...", file=sys.stderr)

    for i in range(num_blocks):
        message_block = padded_bits[i * k:(i + 1) * k].astype(np.int32)
        codeword = np.mod(message_block @ G, 2).astype(np.uint8)
        
        # Verify encoding is correct
        syndrome = np.mod(H @ codeword, 2)
        if np.any(syndrome != 0):
            print(f"Warning: Block {i} failed syndrome check!", file=sys.stderr)
        
        encoded_blocks.append(codeword)

    final_bitstream = np.concatenate(encoded_blocks)
    print(f"Encoding complete. Total output bits: {len(final_bitstream)}", file=sys.stderr)
    return final_bitstream


def bits_to_iats(bits, low_iat, high_iat):
    print(f"Mapping {len(bits)} bits to IAT values...", file=sys.stderr)
    # Map: bit=1 -> low_iat, bit=0 -> high_iat
    iat_list = [str(low_iat) if bit == 1 else str(high_iat) for bit in bits]
    return ",".join(iat_list)


def main():
    parser = argparse.ArgumentParser(
        description="LDPC encoder with Sum-Product decoding support for covert timing channels.",
        usage="%(prog)s <input_file> <low_iat> <high_iat>",
        epilog="Example: %(prog)s secret.txt 1.0 5.0 > times.csv"
    )
    
    parser.add_argument("input_file", help="Input file path")
    parser.add_argument("low_iat", type=float, help="IAT value in ms for bit '1'")
    parser.add_argument("high_iat", type=float, help="IAT value in ms for bit '0'")
    parser.add_argument('-N', type=int, default=N, help=f"Codeword length (default: {N})")
    parser.add_argument('-dv', type=int, default=D_V, help=f"Variable node degree (default: {D_V})")
    parser.add_argument('-dc', type=int, default=D_C, help=f"Check node degree (default: {D_C})")
    parser.add_argument('--seed', type=int, default=SEED, help=f"Seed for deterministic LDPC generation (default: {SEED})")
    args = parser.parse_args()

    # Validate IAT values
    if args.low_iat >= args.high_iat or args.low_iat <= 0:
        print("Error: IAT values must be positive and low_iat must be less than high_iat.", file=sys.stderr)
        sys.exit(1)

    # 1. Read input file to bits
    bits = file_to_bits(args.input_file)
    original_bit_len = len(bits)
    
    # 2. Generate LDPC matrices with seed
    H, G, k = generate_ldpc_matrices(args.N, args.dv, args.dc, args.seed)
    
    # 3. Encode using LDPC
    encoded_bits = encode_ldpc_correct(bits, G, k, H, args.N)
    
    # 4. Convert the final bitstream to IAT values
    iat_string = bits_to_iats(encoded_bits, args.low_iat, args.high_iat)
    
    # 5. Print metadata to stderr (decoder needs this!)
    print(f"\n=== METADATA FOR DECODER ===", file=sys.stderr)
    print(f"Original message length (bits): {original_bit_len}", file=sys.stderr)
    print(f"Encoder parameters:", file=sys.stderr)
    print(f"  low_iat={args.low_iat}, high_iat={args.high_iat}", file=sys.stderr)
    print(f"Decoder command:", file=sys.stderr)
    threshold = (args.low_iat + args.high_iat) / 2
    print(f"  python3 ldpc_decode.py <timing_file> {threshold} --seed {args.seed} -N {args.N} -dv {args.dv} -dc {args.dc} --orig-len {original_bit_len}", file=sys.stderr)
    print(f"============================\n", file=sys.stderr)
    
    # 6. Write the final IAT string to stdout
    print(iat_string)


if __name__ == "__main__":
    main()