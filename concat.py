import glob
import csv

files = sorted(glob.glob("timings_vpn_no_fuzzy_receiver/log_*.txt"))

with open("vpn_no_fuzzy.csv", "w", newline="") as csvfile:
    writer = csv.writer(csvfile)
    for fname in files:
        with open(fname) as f:
            for line in f:
                line = line.strip()
                if line:
                    writer.writerow([line])
