#!/usr/bin/env python3
import sys
from typing import List, Tuple


def read_csv_floats(path: str) -> List[float]:
    """
    Read a CSV file containing numeric values and return a list of floats.
    """
    with open(path, "r") as f:
        return [
            float(x.strip())
            for x in f.read().replace("\n", ",").split(",")
            if x.strip()
        ]


def impact_score(
    exact_vals: List[float],
    fuzzy_vals: List[float],
    thresh: float
) -> Tuple[int, List[Tuple[int, float, float]]]:
    """
    Algorithm 1 (Impact Score) from the paper.

    Counts how many delays cross the decoding threshold after fuzziness
    injection.

    Returns:
        I      : impact score (number of flips)
        flips  : list of (index, exact_value, fuzzy_value)
    """
    if len(exact_vals) != len(fuzzy_vals):
        raise ValueError(
            f"Length mismatch: {len(exact_vals)} vs {len(fuzzy_vals)}"
        )

    I = 0
    flips = []

    for i, (d, d_prime) in enumerate(zip(exact_vals, fuzzy_vals)):
        crossed_threshold = (
            (d < thresh and d_prime >= thresh) or
            (d >= thresh and d_prime < thresh)
        )

        if crossed_threshold:
            I += 1
            flips.append((i, d, d_prime))

    return I, flips


def main():
    if len(sys.argv) < 3:
        print(
            f"Usage: python {sys.argv[0]} <iat_exact.csv> <iat_fuzzy.csv> [tau_ms]"
        )
        sys.exit(1)

    exact_file = sys.argv[1]
    fuzzy_file = sys.argv[2]
    tau_ms = float(sys.argv[3]) if len(sys.argv) > 3 else 100.0

    # Decoding threshold t = 3τ / 2
    thresh = (3.0 * tau_ms) / 2.0

    try:
        exact_vals = read_csv_floats(exact_file)
        fuzzy_vals = read_csv_floats(fuzzy_file)

        I, flips = impact_score(exact_vals, fuzzy_vals, thresh)

        if I == 0:
            print(
                f"✓ Impact score I = 0 "
                f"(checked {len(exact_vals)} delays, threshold = {thresh:.3f} ms)"
            )
        else:
            print(
                f"✗ Impact score I = {I} "
                f"(threshold = {thresh:.3f} ms)"
            )
            for idx, d, d_prime in flips[:10]:
                side_before = "short" if d < thresh else "long"
                side_after  = "short" if d_prime < thresh else "long"
                print(
                    f"  Index {idx}: "
                    f"{d:.3f} ms ({side_before}) → "
                    f"{d_prime:.3f} ms ({side_after})"
                )
            if I > 10:
                print(f"  ... and {I - 10} more flips")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
