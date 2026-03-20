#!/usr/bin/env python3
"""
rs_encode.py
Usage:
  python3 rs_encode.py input.bin 10.0 200.0 -o iat.csv

Encodes a file using Reed-Solomon parameters below,
prefixes 4-byte length + 4-byte CRC32 (big-endian),
chunks into RS_K-sized blocks, zero-pads last block,
RS-encodes each block -> codewords (length RS_N),
then maps encoded bytes -> IAT values (LSB-first bit order).

Bit mapping:
  1 -> min_delay (short)
  0 -> max_delay (long)
"""
import argparse
import os
import struct
import zlib
from reedsolo import RSCodec

# ---- CODE PARAMETERS (tweak if you want) ----
RS_N = 127          # codeword length (symbols)
RS_K = 108          # message length (symbols) per block
NSYM = RS_N - RS_K  # number of parity symbols (nsym)
# ----------------------------------------------

def read_file(path):
    with open(path, "rb") as f:
        return f.read()

def main():
    p = argparse.ArgumentParser(description="RS encoder -> IAT mapper (LSB-first)")
    p.add_argument("input_file", help="input binary file")
    p.add_argument("min_delay", type=float, help="delay (ms) for bit 1 (short)")
    p.add_argument("max_delay", type=float, help="delay (ms) for bit 0 (long)")
    p.add_argument("-o", "--output", default="iat_manual.txt", help="output IAT CSV (default: iat.csv)")
    p.add_argument("-w", "--write-encoded", help="optional: write encoded bytes to this file (debug)")
    args = p.parse_args()

    if not os.path.exists(args.input_file):
        p.error(f"Input file not found: {args.input_file}")
    if not (0 < args.min_delay < args.max_delay):
        p.error("Ensure 0 < min_delay < max_delay")

    payload = read_file(args.input_file)
    orig_len = len(payload)

    # Header: 4-byte length + 4-byte CRC32 (big-endian)
    crc = zlib.crc32(payload) & 0xFFFFFFFF
    header = struct.pack(">I", orig_len) + struct.pack(">I", crc)
    data_with_header = header + payload

    # RS codec: NSYM parity bytes, nsize = RS_N
    rs = RSCodec(NSYM, nsize=RS_N)

    encoded_bytes = bytearray()
    # chunk into RS_K-byte messages
    for i in range(0, len(data_with_header), RS_K):
        chunk = data_with_header[i:i+RS_K]
        if len(chunk) < RS_K:
            chunk = chunk + bytes(RS_K - len(chunk))  # zero pad
        codeword = rs.encode(bytes(chunk))  # returns message + parity => length RS_N
        encoded_bytes.extend(codeword)

    if args.write_encoded:
        with open(args.write_encoded, "wb") as ef:
            ef.write(encoded_bytes)

    # Map encoded bytes -> IAT list (LSB-first)
    iats = []
    min_d = args.min_delay
    max_d = args.max_delay
    for b in encoded_bytes:
        for bit_index in range(8):  # LSB-first: bit 0 .. 7
            bit = (b >> bit_index) & 1
            iats.append(str(min_d if bit else max_d))

    with open(args.output, "w") as out:
        out.write(",".join(iats))

    blocks = len(encoded_bytes) // RS_N
    overhead = (len(encoded_bytes) - len(data_with_header)) / max(1, len(data_with_header)) * 100
    print(f"[i] Input {orig_len} bytes -> header+payload {len(data_with_header)} bytes", file=os.sys.stderr)
    print(f"[i] Encoded {len(encoded_bytes)} bytes in {blocks} RS block(s); overhead ~ {overhead:.2f}%", file=os.sys.stderr)

if __name__ == "__main__":
    main()
