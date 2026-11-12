import csv, math, statistics
from pathlib import Path

ROOT = Path.cwd()
FIXED = ROOT / "runs" / "fixed"
RANDOM = ROOT / "runs" / "random"
CORRECTED = ROOT / "person2_corrected_zero_padded.csv"
OUT = ROOT / "PERSON2_INDEPENDENT_STATS_CHECK.txt"
lines = []

def log(s=""):
    print(s)
    lines.append(str(s))

def load_group(folder, pattern):
    data = {}
    files = sorted(folder.glob(pattern))
    for path in files:
        with path.open(newline="") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames or not {"PC", "MISSES"}.issubset(reader.fieldnames):
                raise ValueError(f"Unexpected CSV header in {path}: {reader.fieldnames}")
            for row in reader:
                pc = row["PC"].strip().lower()
                value = float(row["MISSES"])
                data.setdefault(pc, []).append(value)
    return data, files

log("PERSON 2 — INDEPENDENT STATISTICS CHECK")
log("=" * 70)

fixed, ff = load_group(FIXED, "misses_[0-9][0-9].csv")
random, rf = load_group(RANDOM, "misses_[0-9][0-9].csv")

log(f"Zero-padded fixed files: {len(ff)}")
log(f"Zero-padded random files: {len(rf)}")
log(f"Distinct fixed PCs: {len(fixed)}")
log(f"Distinct random PCs: {len(random)}")
log(f"Union of PCs in raw inputs: {len(set(fixed) | set(random))}")
log("Fixed rows per file: " + str([sum(1 for _ in csv.DictReader(p.open())) for p in ff]))
log("Random rows per file: " + str([sum(1 for _ in csv.DictReader(p.open())) for p in rf]))

if len(ff) != 10 or len(rf) != 10:
    log("FAIL: Expected 10 fixed and 10 random zero-padded files.")
else:
    log("PASS: Expected number of zero-padded files is present.")

if not CORRECTED.exists():
    log("FAIL: Corrected CSV is missing.")
    OUT.write_text("\n".join(lines) + "\n")
    raise SystemExit(1)

with CORRECTED.open(newline="") as f:
    corrected_rows = {r["PC"].strip().lower(): r for r in csv.DictReader(f)}

raw_union = set(fixed) | set(random)
log(f"Corrected result PCs: {len(corrected_rows)}")
log(f"PCs in corrected CSV but not raw zero-padded inputs: {len(set(corrected_rows)-raw_union)}")
log(f"PCs in raw zero-padded inputs but not corrected CSV: {len(raw_union-set(corrected_rows))}")

# Only calculate where raw observations exist for both groups.
# Do not invent missing PC observations or silently fill absent rows with zeros.
computed = {}
for pc in sorted(set(fixed) & set(random)):
    x, y = fixed[pc], random[pc]
    if len(x) < 2 or len(y) < 2:
        computed[pc] = ("INSUFFICIENT_SAMPLES", None, None)
        continue

    mx, my = statistics.mean(x), statistics.mean(y)
    vx, vy = statistics.variance(x), statistics.variance(y)
    se2 = vx / len(x) + vy / len(y)
    if se2 == 0:
        computed[pc] = ("UNDEFINED_ZERO_SE", mx, my)
        continue

    t = (mx - my) / math.sqrt(se2)
    a, b = vx / len(x), vy / len(y)
    df_den = (a*a)/(len(x)-1) + (b*b)/(len(y)-1)
    df = (a+b)**2 / df_den if df_den else float("nan")
    computed[pc] = ("FINITE", t, df)

log()
log("INDEPENDENT RECOMPUTATION")
log(f"PCs with observations in both groups: {len(computed)}")
log(f"Finite Welch statistics: {sum(v[0]=='FINITE' for v in computed.values())}")
log(f"Zero-SE undefined statistics: {sum(v[0]=='UNDEFINED_ZERO_SE' for v in computed.values())}")
log(f"Insufficient samples: {sum(v[0]=='INSUFFICIENT_SAMPLES' for v in computed.values())}")

# Compare only PCs where this script has enough data to calculate a valid t.
mismatches = []
for pc, (status, t, df) in computed.items():
    if status != "FINITE" or pc not in corrected_rows:
        continue
    row = corrected_rows[pc]
    try:
        recorded = float(row["WELCH_T"])
        nfixed = int(row["N_FIXED"])
        nrandom = int(row["N_RANDOM"])
        if not math.isclose(t, recorded, rel_tol=1e-5, abs_tol=1e-6):
            mismatches.append((pc, t, recorded, "t mismatch"))
        if nfixed != len(fixed[pc]) or nrandom != len(random[pc]):
            mismatches.append((pc, len(fixed[pc]), len(random[pc]),
                               f"sample-size mismatch: CSV says {nfixed}/{nrandom}"))
    except (ValueError, KeyError) as e:
        mismatches.append((pc, "", "", f"comparison error: {e}"))

log(f"Comparisons against corrected CSV: {sum(v[0]=='FINITE' and pc in corrected_rows for pc,v in computed.items())}")
log(f"Mismatches found: {len(mismatches)}")
for item in mismatches[:30]:
    log("MISMATCH: " + repr(item))

log()
log("ZERO-STANDARD-ERROR ROWS IN CORRECTED CSV")
zero_rows = 0
for pc, row in corrected_rows.items():
    try:
        if float(row["STANDARD_ERROR"]) == 0:
            zero_rows += 1
            log(f"{pc}: status={row['STATISTIC_STATUS']}, "
                f"t={row['WELCH_T']}, means={row['FIXED_MEAN']}/{row['RANDOM_MEAN']}, "
                f"variances={row['FIXED_VARIANCE']}/{row['RANDOM_VARIANCE']}")
    except (ValueError, KeyError):
        pass
log(f"Total corrected rows with zero standard error: {zero_rows}")

log()
log("VERDICT")
if len(corrected_rows) != len(raw_union):
    log("NOT VERIFIED: corrected CSV row count/PC coverage differs from the raw zero-padded input union.")
if mismatches:
    log("NOT VERIFIED: at least one Welch statistic or sample count differs from direct recomputation.")
if len(set(corrected_rows) - raw_union):
    log("NOT VERIFIED: corrected CSV contains PCs absent from these raw inputs.")
if not mismatches and set(corrected_rows) == raw_union and len(computed) == len(raw_union):
    log("PASS: PC coverage and computed finite statistics match these raw inputs.")
else:
    log("Review the counts above before using this CSV as a verified final result.")
log()
log("This check intentionally does not merge the non-zero-padded files.")
OUT.write_text("\n".join(lines) + "\n")
print(f"\nReport saved to: {OUT}")
