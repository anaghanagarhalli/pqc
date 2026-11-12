import csv, random, math, statistics, subprocess, sys
from pathlib import Path

BASE = Path(".")
SCRIPT = BASE / "phase5_cache_variance.py"
OUT = BASE / "person2_rebuilt_full"
OUT.mkdir(exist_ok=True)

def run_trace(group, n):
    trace = BASE / "runs" / group / f"trace_{n}.csv"
    if not trace.exists():
        raise FileNotFoundError(f"Missing full trace: {trace}")

    # Use deterministic, explicitly recorded seeds for reproducibility.
    seed = (10000 if group == "fixed" else 20000) + n
    dest = OUT / f"{group}_misses_{n:02d}.csv"

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--trace", str(trace),
         "--seed", str(seed), "--output", str(dest)],
        text=True, capture_output=True
    )
    if result.returncode:
        raise RuntimeError(f"{trace} failed:\n{result.stderr}")

    counts = {}
    with dest.open(newline="") as f:
        for row in csv.DictReader(f):
            counts[int(row["PC"], 16)] = int(row["MISSES"])
    return counts, seed, result.stdout.strip()

def welch(a, b):
    ma, mb = statistics.mean(a), statistics.mean(b)
    va = statistics.variance(a) if len(a) > 1 else float("nan")
    vb = statistics.variance(b) if len(b) > 1 else float("nan")
    denom2 = va / len(a) + vb / len(b)
    if not math.isfinite(denom2) or denom2 <= 0:
        return ma, mb, va, vb, float("nan"), float("nan")
    t = (ma - mb) / math.sqrt(denom2)
    x, y = va / len(a), vb / len(b)
    df = (x + y) ** 2 / (x*x/(len(a)-1) + y*y/(len(b)-1)) \
        if (x*x + y*y) > 0 else float("nan")
    return ma, mb, va, vb, t, df

fixed, random = [], []
seeds, runlogs = [], []
for group, dest in (("fixed", fixed), ("random", random)):
    for n in range(1, 11):
        counts, seed, log = run_trace(group, n)
        dest.append(counts)
        seeds.append((group, n, seed))
        runlogs.append((group, n, log))

all_pcs = sorted(set().union(*(set(x) for x in fixed + random)))
stats_path = OUT / "person2_full_trace_welch_results.csv"
undefined = 0
high = 0

with stats_path.open("w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["PC", "fixed_mean", "random_mean", "fixed_variance",
                "random_variance", "welch_t", "welch_df", "abs_t_gt_4_5",
                "status"])
    for pc in all_pcs:
        # A PC not present in a full trace has zero misses for that run.
        a = [d.get(pc, 0) for d in fixed]
        b = [d.get(pc, 0) for d in random]
        ma, mb, va, vb, t, df = welch(a, b)
        valid = math.isfinite(t)
        flag = valid and abs(t) > 4.5
        undefined += not valid
        high += flag
        w.writerow([
            f"0x{pc:08x}", f"{ma:.8g}", f"{mb:.8g}",
            f"{va:.8g}", f"{vb:.8g}",
            f"{t:.8g}" if valid else "UNDEFINED",
            f"{df:.8g}" if math.isfinite(df) else "UNDEFINED",
            "YES" if flag else "NO",
            "FINITE" if valid else "ZERO_OR_INVALID_STANDARD_ERROR"
        ])

report = OUT / "PERSON2_FULL_TRACE_REBUILD_REPORT.txt"
with report.open("w") as f:
    f.write("PERSON 2 — FULL TRACE REBUILD REPORT\n")
    f.write("====================================\n")
    f.write("Original traces and miss CSVs were not overwritten.\n")
    f.write("Inputs: runs/fixed/trace_1.csv through trace_10.csv and\n")
    f.write("        runs/random/trace_1.csv through trace_10.csv\n\n")
    f.write("Method: regenerated per-PC cache misses using phase5_cache_variance.py.\n")
    f.write("Seeds are newly assigned deterministic seeds, not recovered historical seeds.\n")
    f.write("Therefore this is a reproducible reconstruction, not proof of original-run identity.\n")
    f.write("Missing PCs in a generated miss CSV are treated as zero misses.\n\n")
    f.write(f"PCs in union: {len(all_pcs)}\n")
    f.write(f"Finite Welch t-statistics: {len(all_pcs)-undefined}\n")
    f.write(f"Undefined statistics: {undefined}\n")
    f.write(f"Finite |t| > 4.5: {high}\n\n")
    f.write("Generated seeds and cache simulator outputs:\n")
    for group, n, seed in seeds:
        f.write(f"{group} run {n:02d}: seed={seed}\n")
    for group, n, log in runlogs:
        f.write(f"{group} run {n:02d}: {log}\n")
    f.write("\nOutput CSV: person2_full_trace_welch_results.csv\n")
    f.write("Per-run reconstructed miss files are stored in this directory.\n")

print(report.read_text())
print(f"\nFiles saved under: {OUT.resolve()}")
print(f"Statistics CSV: {stats_path.resolve()}")
