import csv
import math
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

BASE = Path.home() / "pqc-cache-project/phase5_svc/runs"
SVS = Path.home() / "pqc-cache-project/phase5_svc/svs_results.csv"
OUT = Path.home() / "pqc-cache-project/phase6"

# -------------------------------------------------
# 1. Per-run cache-miss heatmap
# -------------------------------------------------

records = []

for condition in ["fixed", "random"]:
    for run in range(1, 11):
        miss_file = BASE / condition / f"misses_{run:02d}.csv"

        with open(miss_file, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                records.append({
                    "Condition": condition.upper(),
                    "Run": run,
                    "PC": row["PC"],
                    "Misses": int(row["MISSES"])
                })

df = pd.DataFrame(records)

heat = df.pivot_table(
    index="PC",
    columns=["Condition", "Run"],
    values="Misses",
    aggfunc="sum",
    fill_value=0
)

# Limit visualization to PCs with the largest overall activity
top_pcs = (
    df.groupby("PC")["Misses"]
      .sum()
      .sort_values(ascending=False)
      .head(40)
      .index
)

heat = heat.loc[top_pcs]

plt.figure(figsize=(15, 10))
plt.imshow(heat.values, aspect="auto")
plt.xticks(
    range(len(heat.columns)),
    [f"{c[0]}-{c[1]}" for c in heat.columns],
    rotation=90
)
plt.yticks(range(len(heat.index)), heat.index)
plt.xlabel("Execution run")
plt.ylabel("Program Counter")
plt.title("Per-PC Cache Miss Heatmap")
plt.colorbar(label="Cache misses")
plt.tight_layout()
plt.savefig(OUT / "cache_miss_heatmap.png", dpi=200)
plt.close()

# -------------------------------------------------
# 2. SVS leakage plot with 95% confidence interval
# -------------------------------------------------

svs = pd.read_csv(SVS)

svs["SVS_ABS"] = svs["SVS"].abs()

high = svs[svs["RISK"].astype(str).str.strip() == "HIGH-RISK"].copy()

# finite SVS only for the confidence-interval visualization
finite = pd.to_numeric(high["SVS_ABS"], errors="coerce")
finite = finite.replace([math.inf, -math.inf], math.nan)

high["SVS_FINITE"] = finite

finite_high = high.dropna(subset=["SVS_FINITE"]).copy()

plt.figure(figsize=(12, 7))

if not finite_high.empty:
    x = range(len(finite_high))
    y = finite_high["SVS_FINITE"].values

    plt.errorbar(
        x,
        y,
        yerr=1.96 * finite_high["SVS_FINITE"].std(ddof=1)
        if len(finite_high) > 1
        else 0,
        fmt="o"
    )

    plt.xticks(
        list(x),
        finite_high["PC"].astype(str),
        rotation=90
    )

plt.axhline(4.5, linestyle="--", label="High-risk threshold |t| = 4.5")
plt.xlabel("High-risk PC")
plt.ylabel("SVS = |Welch t|")
plt.title("Side-Channel Vulnerability Scores")
plt.legend()
plt.tight_layout()
plt.savefig(OUT / "svs_leakage_confidence.png", dpi=200)
plt.close()

# -------------------------------------------------
# 3. SVS distribution
# -------------------------------------------------

all_finite = pd.to_numeric(svs["SVS"], errors="coerce")
all_finite = all_finite.replace([math.inf, -math.inf], math.nan).dropna()

plt.figure(figsize=(10, 6))
plt.hist(all_finite, bins=30)
plt.axvline(4.5, linestyle="--", label="High-risk threshold")
plt.xlabel("SVS = |Welch t|")
plt.ylabel("Number of instructions")
plt.title("SVS Distribution")
plt.legend()
plt.tight_layout()
plt.savefig(OUT / "svs_distribution.png", dpi=200)
plt.close()

print("Created:")
print("  cache_miss_heatmap.png")
print("  svs_leakage_confidence.png")
print("  svs_distribution.png")
