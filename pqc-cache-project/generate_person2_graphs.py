import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import numpy as np

ROOT = Path.home() / "pqc-cache-project"
OUT = ROOT / "PERSON2_NEW_GRAPHS"
OUT.mkdir(exist_ok=True)

# --------------------------------------------------
# GRAPH 1: WR2 fixed vs randomized modeled misses
# --------------------------------------------------
run_dir = OUT / "WR2_MODELED_RUNS"

fixed = []
randomized = []

for f in sorted(run_dir.glob("trace_*_misses.csv")):
    df = pd.read_csv(f)
    total = int(df["MISSES"].sum())

    if f.name.startswith("trace_"):
        original = f.name.replace("_misses.csv", ".csv")
        if (ROOT / "phase5_svc/runs/fixed" / original).exists():
            fixed.append(total)
        elif (ROOT / "phase5_svc/runs/random" / original).exists():
            randomized.append(total)

if fixed and randomized:
    plt.figure(figsize=(9, 6))
    plt.boxplot([fixed, randomized],
                tick_labels=["Fixed input", "Randomized input"])
    plt.ylabel("Modeled cache misses per trace")
    plt.title("WR2: Fixed vs Randomized Cache-Miss Comparison")
    plt.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUT / "WR2_Fixed_vs_Random_Modeled_Misses.jpeg",
                dpi=300, bbox_inches="tight")
    plt.close()
    print("Created WR2 graph")
else:
    print("WR2 graph skipped: no valid observations found")

# --------------------------------------------------
# GRAPH 2: WR3 per-PC mean misses
# --------------------------------------------------
wr3 = pd.read_csv(ROOT / "phase5_svc/svs_results.csv")
wr3["PC"] = wr3["PC"].astype(str)

wr3 = wr3.sort_values("SVS", ascending=False).head(20)

x = np.arange(len(wr3))
width = 0.38

plt.figure(figsize=(15, 7))
plt.bar(x - width/2, wr3["FIXED_MEAN_MISSES"],
        width, label="Fixed")
plt.bar(x + width/2, wr3["RANDOM_MEAN_MISSES"],
        width, label="Randomized")

plt.xticks(x, wr3["PC"], rotation=70, fontsize=7)
plt.ylabel("Mean cache misses")
plt.xlabel("Program counter (PC)")
plt.title("WR3: Top 20 PCs by Supplied SVS Score")
plt.legend()
plt.grid(axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig(OUT / "WR3_Per_PC_Mean_Misses.jpeg",
            dpi=300, bbox_inches="tight")
plt.close()
print("Created WR3 graph")

# --------------------------------------------------
# GRAPH 3: Cache associativity
# --------------------------------------------------
assoc = pd.read_csv(ROOT / "phase6/associativity_tradeoff.csv")

plt.figure(figsize=(9, 6))
bars = plt.bar(
    assoc["ASSOCIATIVITY"].astype(str),
    assoc["MISSES"]
)

plt.xlabel("Cache associativity")
plt.ylabel("Cache misses")
plt.title("Cache Associativity vs Cache Misses")

for bar, value in zip(bars, assoc["MISSES"]):
    plt.text(bar.get_x() + bar.get_width()/2,
             bar.get_height(),
             str(value), ha="center", va="bottom")

plt.grid(axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig(OUT / "Cache_Associativity_Comparison.jpeg",
            dpi=300, bbox_inches="tight")
plt.close()
print("Created associativity graph")

print("\nAll available graphs saved in:", OUT)
