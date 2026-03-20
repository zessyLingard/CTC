#!/usr/bin/env python3
import sys
import numpy as np

np.random.seed(0)

def inject_fuzzy(x_ms, tau_ms):
    """
    Fuzzy IAT injection with non-overlapping symbol regions.
    """
    thresh = (3 * tau_ms) / 2.0
    eps = 0.001  # resolution guard

    if x_ms < thresh:
        # Truncated Gaussian: strictly below thresh
        res = abs(np.random.normal(0.0, scale=thresh / 7.0))
        while res >= thresh:
            res = abs(np.random.normal(0.0, scale=thresh / 7.0))
        return res
    else:
        # Uniform: strictly above thresh
        return float(np.random.choice(
            np.arange(thresh + eps, 2.4 * tau_ms, eps)
        ))

def main():
    if len(sys.argv) != 3:
        print(f"Usage: python {sys.argv[0]} <input_csv> <tau_ms>", file=sys.stderr)
        sys.exit(1)

    tau_ms = float(sys.argv[2])

    with open(sys.argv[1], 'r') as f:
        iat_ms = [float(v) for v in f.read().replace('\n', ',').split(',') if v.strip()]

    fuzzed = [inject_fuzzy(x, tau_ms) for x in iat_ms]
    print(','.join(f"{x:.3f}" for x in fuzzed))

if __name__ == "__main__":
    main()
