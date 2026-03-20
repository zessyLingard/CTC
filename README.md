# CCEAP: Covert Channel Educational Analysis Protocol

CCEAP is a protocol and toolkit for teaching and experimenting with covert channels (network steganography), focusing on timing-based channels and error-correcting codes (ECC). This guide describes the updated workflow for preparing, sending, and decoding covert channel payloads using BCH and Reed-Solomon (RS) codes.

## Workflow Overview

1. **Prepare Payload**
   - Read your file/data.
   - Split payload into fixed-size blocks for ECC (bits for BCH, bytes for RS).
   - Pad the last block if needed.

2. **ECC Encode**
   - Encode each block using BCH or RS.
   - Serialize codewords to a bit stream.

3. **Map Bits to IATs**
   - Convert bits to inter-arrival times (IATs) for covert timing mapping.

## Example Usage
### Remember to run make to create the object files.

### 1. Start the Server

Run the server and log output:

```
./server -P 9999 -q > log.txt
```

### 2. Prepare and Send Payload

#### BCH Encoding (C code)

Encode your file and send using timing channel:

```
./client -D 127.0.0.1 -P 9999 -t $(./bch_encode secret_1KB.txt 20 50)
```

#### Reed-Solomon Encoding

First, convert your payload to a timings file (long IATs), then send:

```
./client -D 127.0.0.1 -P 9999 -f timings.txt
```

### 3. Extract Timings from Server Log

After transmission, extract timing data:

```
grep "time diff to prev pkt" log.txt | awk '{printf "%.3f\n", $NF}' > timing.txt
```

### 4. Decode Payload

#### BCH Decoding

Remove trailing nulls after decoding:

```
./bch_decode 8 255 8 timing.txt 0.015 | sed 's/\x00*$//' > res.txt
```

#### Reed-Solomon Decoding (Python)

```
python3 rs_decode.py <filename> <threshold>
```

## Author

CCEAP was created by Steffen Wendzel ([www.wendzel.de](https://www.wendzel.de), steffen (at) wendzel (dot) de).

