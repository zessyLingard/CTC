#!/usr/bin/env python3
"""
rs_decode.py
Usage:
  python3 rs_decode.py timing.txt 150 -o recovered.bin
  python3 rs_decode.py timing.txt auto -o recovered.bin

Reads IATs (commas or whitespace), threshold in ms or 'auto'.
Maps to bits (<=threshold -> 1, else 0), packs LSB-first,
RS-decodes per RS_N block, extracts header: [4-byte length][4-byte CRC32],
writes recovered payload to file or stdout.
"""
import argparse
import re
import struct
import sys
import zlib
from reedsolo import RSCodec, ReedSolomonError

# ---- CODE PARAMETERS (must match encoder) ----
RS_N = 127
RS_K = 108
NSYM = RS_N - RS_K
# ---------------------------------------------

def parse_iats(filename):
    with open(filename, "r") as f:
        s = f.read()
    nums = re.findall(r'\d+(?:\.\d+)?', s)
    return [float(x) for x in nums]

def auto_threshold(values):
    vals = sorted(values)
    if len(vals) < 2:
        return vals[0] if vals else 0.0
    max_gap = 0.0
    threshold = (vals[0] + vals[-1]) / 2.0
    for a, b in zip(vals, vals[1:]):
        gap = b - a
        if gap > max_gap:
            max_gap = gap
            threshold = (a + b) / 2.0
    return threshold

def bits_to_bytes_lsb(bits):
    out = bytearray()
    cur = 0
    cnt = 0
    for bit in bits:
        cur |= (bit << cnt)
        cnt += 1
        if cnt == 8:
            out.append(cur)
            cur = 0
            cnt = 0
    if cnt:
        out.append(cur)
    return out

def main():
    p = argparse.ArgumentParser(description="RS decode from IATs -> recover original payload")
    p.add_argument("iat_file", help="IAT input file (commas or whitespace allowed)")
    p.add_argument("threshold", help="threshold in ms (e.g. 150) or 'auto'")
    p.add_argument("-o", "--out", help="optional: write recovered payload to file")
    args = p.parse_args()

    iats = parse_iats(args.iat_file)
    if not iats:
        print("[x] No IAT values found", file=sys.stderr)
        sys.exit(2)

    if args.threshold == "auto":
        threshold = auto_threshold(iats)
        print(f"[i] Auto threshold = {threshold:.3f} ms", file=sys.stderr)
    else:
        threshold = float(args.threshold)
        print(f"[i] Using threshold = {threshold:.3f} ms", file=sys.stderr)

    bits = [1 if v <= threshold else 0 for v in iats]
    ones = sum(bits)
    zeros = len(bits) - ones
    print(f"[i] Bits: {len(bits)} total (ones={ones}, zeros={zeros})", file=sys.stderr)

    data_bytes = bits_to_bytes_lsb(bits)
    print(f"[i] Packed into {len(data_bytes)} bytes", file=sys.stderr)

    rs = RSCodec(NSYM, nsize=RS_N)
    decoded_all = bytearray()

    if len(data_bytes) >= RS_N:
        nblocks = len(data_bytes) // RS_N
        print(f"[i] Decoding {nblocks} full RS blocks (size {RS_N})", file=sys.stderr)
        for i in range(nblocks):
            block = data_bytes[i*RS_N:(i+1)*RS_N]
            try:
                res = rs.decode(block)
                # res is (decoded_msg, decoded_msg_with_ecc, errata_pos) in reedsolo
                decoded_msg = res[0] if isinstance(res, (tuple, list)) else res
                # decoded_msg should be RS_K bytes (original message length for this block)
                decoded_all.extend(decoded_msg[:RS_K])
                print(f"[✓] Block {i+1} OK", file=sys.stderr)
            except ReedSolomonError as e:
                print(f"[x] Block {i+1} failed: {e}", file=sys.stderr)
    else:
        # try single codeword decode or padded decode
        print("[i] Buffer < RS_N; attempting single-codeword decode", file=sys.stderr)
        try:
            res = rs.decode(data_bytes)
            decoded_msg = res[0] if isinstance(res, (tuple, list)) else res
            decoded_all.extend(decoded_msg[:RS_K])
            print("[✓] Single RS decode OK", file=sys.stderr)
        except Exception as e:
            print(f"[x] Single RS decode failed: {e}", file=sys.stderr)
            pad_block = data_bytes + bytes(RS_N - len(data_bytes))
            try:
                res = rs.decode(pad_block)
                decoded_msg = res[0] if isinstance(res, (tuple, list)) else res
                decoded_all.extend(decoded_msg[:RS_K])
                print("[✓] Padded single RS decode OK", file=sys.stderr)
            except Exception as e2:
                print(f"[x] Padded decode failed: {e2}", file=sys.stderr)
                print("[x] Cannot decode RS data", file=sys.stderr)
                sys.exit(2)

    if not decoded_all:
        print("[x] No decoded bytes recovered", file=sys.stderr)
        sys.exit(2)

    if len(decoded_all) < 8:
        print("[x] Decoded data shorter than 8 bytes, can't read header", file=sys.stderr)
        sys.exit(2)

    orig_len = struct.unpack(">I", decoded_all[:4])[0]
    got_crc = struct.unpack(">I", decoded_all[4:8])[0]
    payload = decoded_all[8:8+orig_len]

    calc_crc = zlib.crc32(payload) & 0xFFFFFFFF
    if calc_crc != got_crc:
        print(f"[!] CRC mismatch: expected {got_crc:08x}, calc {calc_crc:08x}", file=sys.stderr)
    else:
        print(f"[i] CRC OK (0x{calc_crc:08x})", file=sys.stderr)

    print(f"[i] Recovered payload {len(payload)} bytes (original length recorded {orig_len})", file=sys.stderr)

    if args.out:
        with open(args.out, "wb") as f:
            f.write(payload)
        print(f"[i] Wrote payload to '{args.out}'", file=sys.stderr)
    else:
        try:
            sys.stdout.write(payload.decode("utf-8"))
        except UnicodeDecodeError:
            sys.stdout.buffer.write(payload)

if __name__ == "__main__":
    main()
