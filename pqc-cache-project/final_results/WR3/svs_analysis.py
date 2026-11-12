#!/usr/bin/env python3

import csv
import math
from pathlib import Path

BASE = Path.home() / "pqc-cache-project/phase5_svc/runs"
FIXED = BASE / "fixed"
RANDOM = BASE / "random"
OUTPUT = Path.home() / "pqc-cache-project/phase5_svc/svs_results.csv"

def load_distribution(path):
    data = {}
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            data[int(row["PC"], 16)] = int(row["MISSES"])
    return data

def sample_variance(values, mean):
    n = len(values)
    if n < 2:
        return 0.0
    return sum((x - mean) ** 2 for x in values) / (n - 1)

fixed_data = [
    load_distribution(FIXED / f"misses_{i:02d}.csv")
    for i in range(1, 11)
]

random_data = [
    load_distribution(RANDOM / f"misses_{i:02d}.csv")
    for i in range(1, 11)
]

pcs = sorted(set().union(*(d.keys() for d in fixed_data + random_data)))

results = []

for pc in pcs:
    fixed_values = [d.get(pc, 0) for d in fixed_data]
    random_values = [d.get(pc, 0) for d in random_data]

    nf = len(fixed_values)
    nr = len(random_values)

    mf = sum(fixed_values) / nf
    mr = sum(random_values) / nr

    vf = sample_variance(fixed_values, mf)
    vr = sample_variance(random_values, mr)

    denominator = math.sqrt(vf / nf + vr / nr)

    if denominator == 0.0:
        t_value = 0.0 if mf == mr else math.inf
        df = math.inf
    else:
        t_value = (mf - mr) / denominator

        numerator = (vf / nf + vr / nr) ** 2
        denominator_df = 0.0

        if nf > 1:
            denominator_df += (vf / nf) ** 2 / (nf - 1)
        if nr > 1:
            denominator_df += (vr / nr) ** 2 / (nr - 1)

        df = numerator / denominator_df if denominator_df else math.inf

    svs = abs(t_value)
    risk = "HIGH-RISK" if svs > 4.5 else "NORMAL"

    results.append([
        f"{pc:016x}",
        mf,
        mr,
        vf,
        vr,
        t_value,
        df,
        svs,
        risk,
    ])

with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([
        "PC",
        "FIXED_MEAN_MISSES",
        "RANDOM_MEAN_MISSES",
        "FIXED_VARIANCE",
        "RANDOM_VARIANCE",
        "WELCH_T",
        "DEGREES_OF_FREEDOM",
        "SVS",
        "RISK",
    ])
    writer.writerows(results)

high_risk = [r for r in results if r[-1] == "HIGH-RISK"]

print(f"Instructions analysed : {len(results)}")
print(f"High-risk instructions: {len(high_risk)}")
print(f"SVS threshold         : |t| > 4.5")
print(f"Results file          : {OUTPUT}")

print("\nHigh-risk regions:")
if high_risk:
    for r in sorted(high_risk, key=lambda x: x[7], reverse=True):
        print(
            f"PC={r[0]}  "
            f"fixed_mean={r[1]:.4f}  "
            f"random_mean={r[2]:.4f}  "
            f"t={r[5]:.4f}  "
            f"SVS={r[7]:.4f}"
        )
else:
    print("None")
