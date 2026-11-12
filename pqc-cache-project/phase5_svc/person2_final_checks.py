#!/usr/bin/env python3
import csv
import math
import subprocess
from pathlib import Path
from datetime import datetime

ROOT = Path.home() / "pqc-cache-project"
BASE = ROOT / "phase5_svc"
ELF = BASE / "phase5_fixed.elf"

# Conservative 95% two-sided Student-t critical values.
# For fractional df, use the next lower integer df.
T95 = {
    1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571,
    6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
    11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131,
    16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086,
    21: 2.080, 22: 2.074, 23: 2.069, 24: 2.064, 25: 2.060,
    26: 2.056, 27: 2.052, 28: 2.048, 29: 2.045, 30: 2.042
}

def load_csv(path):
    data = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            data[int(row["PC"], 16)] = float(row["MISSES"])
    return data

def variance(values, mean):
    if len(values) < 2:
        return float("nan")
    return sum((x - mean) ** 2 for x in values) / (len(values) - 1)

def analyze(prefix, output_name):
    fixed_files = ([BASE / "runs/fixed" / f"misses_{i:02d}.csv" for i in range(1, 11)]
                   if prefix == "misses_[0-9][0-9].csv" else
                   [BASE / "runs/fixed" / f"misses_{i}.csv" for i in range(1, 11)])
    random_files = ([BASE / "runs/random" / f"misses_{i:02d}.csv" for i in range(1, 11)]
                    if prefix == "misses_[0-9][0-9].csv" else
                    [BASE / "runs/random" / f"misses_{i}.csv" for i in range(1, 11)])
    output = BASE / output_name

    if len(fixed_files) != 10 or len(random_files) != 10:
        print(f"SKIPPED {prefix}: expected 10 files per group; "
              f"found fixed={len(fixed_files)}, random={len(random_files)}")
        return []

    fixed = [load_csv(p) for p in fixed_files]
    random = [load_csv(p) for p in random_files]
    pcs = sorted(set().union(*(d.keys() for d in fixed + random)))
    results = []

    for pc in pcs:
        # Missing PCs are treated as zero misses, consistent with the old script.
        x = [d.get(pc, 0.0) for d in fixed]
        y = [d.get(pc, 0.0) for d in random]
        nx, ny = len(x), len(y)
        mx, my = sum(x)/nx, sum(y)/ny
        vx, vy = variance(x, mx), variance(y, my)
        a, b = vx/nx, vy/ny
        se = math.sqrt(a+b) if math.isfinite(vx+vy) else float("nan")
        diff = mx-my
        df_den = (a*a/(nx-1) if nx > 1 else 0) + \
                 (b*b/(ny-1) if ny > 1 else 0)

        if not math.isfinite(se):
            t, df, lo, hi, status = float("nan"), float("nan"), "", "", "INSUFFICIENT_DATA"
        elif se == 0:
            t, df, lo, hi = float("nan"), float("nan"), "", ""
            status = "UNDEFINED_ZERO_STANDARD_ERROR"
        else:
            t = diff/se
            df = (a+b)**2/df_den if df_den > 0 else float("nan")
            if math.isfinite(df) and df >= 1:
                crit = T95.get(min(30, int(df)), 1.96)
                lo, hi = diff-crit*se, diff+crit*se
                status = "FINITE_WELCH_T"
            else:
                lo, hi = "", ""
                status = "FINITE_T_CI_UNAVAILABLE_DF"

        risk = ("HIGH-RISK" if math.isfinite(t) and abs(t) > 4.5
                else "NORMAL" if math.isfinite(t) else "UNDEFINED")

        results.append({
            "PC": f"0x{pc:016x}", "N_FIXED": nx, "N_RANDOM": ny,
            "FIXED_MEAN": mx, "RANDOM_MEAN": my,
            "MEAN_DIFFERENCE_FIXED_MINUS_RANDOM": diff,
            "FIXED_VARIANCE": vx, "RANDOM_VARIANCE": vy,
            "STANDARD_ERROR": se, "WELCH_T": t, "WELCH_DF": df,
            "CI95_LOW_APPROX": lo, "CI95_HIGH_APPROX": hi,
            "STATISTIC_STATUS": status, "RISK": risk
        })

    fields = list(results[0].keys()) if results else []
    with open(output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in results:
            writer.writerow({
                k: (f"{v:.8g}" if isinstance(v, float) and math.isfinite(v) else v)
                for k, v in r.items()
            })

    high = [r for r in results if r["RISK"] == "HIGH-RISK"]
    undefined = [r for r in results if r["RISK"] == "UNDEFINED"]
    print(f"\nDataset pattern: {prefix}")
    print(f"Fixed runs: {len(fixed_files)} | Random runs: {len(random_files)}")
    print(f"PCs analysed: {len(results)}")
    print(f"Finite |t| > 4.5: {len(high)}")
    print(f"Undefined statistics: {len(undefined)}")
    print(f"Saved: {output}")
    return results

print("PERSON 2: PRESERVING ORIGINAL FILES")
print("Started:", datetime.now().isoformat(timespec="seconds"))

# Keep these two filename families separate: they have different contents.
old_results = analyze("misses_[0-9][0-9].csv",
                      "person2_corrected_zero_padded.csv")
full_results = analyze("misses_[0-9].csv",
                       "person2_corrected_full_runs.csv")

# Map PCs from the full-run dataset using the ELF and its debug information.
mapping_path = BASE / "person2_pc_source_mapping.csv"
mapping_results = full_results or old_results
if mapping_results and ELF.exists():
    addresses = [int(r["PC"], 16) for r in mapping_results
                 if r["RISK"] in ("HIGH-RISK", "UNDEFINED")]
    with open(mapping_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["PC", "FUNCTION_AND_SOURCE_FROM_ADDR2LINE"])
        for pc in addresses:
            try:
                proc = subprocess.run(
                    ["riscv64-unknown-elf-addr2line", "-f", "-C", "-i",
                     "-e", str(ELF), hex(pc)],
                    capture_output=True, text=True, check=True
                )
                lines = [s.strip() for s in proc.stdout.splitlines() if s.strip()]
                writer.writerow([f"0x{pc:016x}", " | ".join(lines)])
            except Exception as e:
                writer.writerow([f"0x{pc:016x}", f"MAPPING_ERROR: {e}"])
    print("Saved source mapping:", mapping_path)
else:
    print("Source mapping skipped: no analysis data or ELF unavailable.")

report = BASE / "person2_findings_summary.txt"
with open(report, "w") as f:
    f.write("PERSON 2 — STATISTICAL VALIDATION AND SOURCE MAPPING\n")
    f.write("====================================================\n\n")
    f.write("Original analysis and CSV were not modified.\n")
    f.write("The zero-padded and non-zero-padded CSV families were analysed separately.\n")
    f.write("Missing PCs were assigned zero misses, matching the original script.\n\n")
    f.write("Welch t-statistic: (fixed mean - random mean) / standard error.\n")
    f.write("If both group variances are zero, the standard error is zero; the t-statistic\n")
    f.write("is undefined whether the means differ or are equal. Do not report infinity\n")
    f.write("as a conventional Welch t-statistic.\n\n")
    f.write("Confidence intervals are approximate 95% Welch intervals using a conservative\n")
    f.write("integer-df t critical-value table. For df > 30, 1.96 is used as a normal\n")
    f.write("approximation. These intervals are not exact and should be labelled accordingly.\n\n")
    f.write("The three workflows previously described must remain separate:\n")
    f.write("1. Broad configuration sweep: six crypto kernels reportedly had zero flagged\n")
    f.write("   locations; LEAKY positive control showed detection.\n")
    f.write("2. Per-PC cache-miss analysis: 10 fixed and 10 random runs; previous CSV claimed\n")
    f.write("   194 PCs and 13 high-risk PCs. The present script checks the current inputs\n")
    f.write("   independently because their row counts do not match that previous CSV.\n")
    f.write("3. Independent timing experiment: baseline reportedly showed no mean difference;\n")
    f.write("   lookup had unequal means with zero variance; branch injection showed a timing\n")
    f.write("   difference. Do not combine its timing values with cache-miss t-statistics.\n\n")
    f.write("A high |t| is evidence of a statistical difference in this sample, not by itself\n")
    f.write("proof of exploitable leakage. Source mapping is based on the selected ELF and\n")
    f.write("debug info; verify the exact build corresponds to the measured traces.\n")
print("Saved findings summary:", report)
print("\nDONE. Review the new files before using results in your paper.")
