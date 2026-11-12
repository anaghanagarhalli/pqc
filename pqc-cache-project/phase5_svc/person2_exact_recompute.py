import csv, math, statistics
from pathlib import Path

BASE = Path(".")
OUT = BASE / "PERSON2_EXACT_RECOMPUTE.txt"

def read(path):
    with open(path, newline="") as f:
        return {
            f"0x{int(r['PC'].strip(), 16):016x}": float(r["MISSES"])
            for r in csv.DictReader(f)
        }

def load_group(group):
    files = [BASE / "runs" / group / f"misses_{i:02d}.csv"
             for i in range(1, 11)]
    missing = [str(p) for p in files if not p.is_file()]
    if missing:
        raise FileNotFoundError("\n".join(missing))
    return [read(p) for p in files]

def welch(x, y):
    mx, my = statistics.mean(x), statistics.mean(y)
    vx, vy = statistics.variance(x), statistics.variance(y)
    se2 = vx / len(x) + vy / len(y)
    if se2 == 0:
        return mx, my, vx, vy, 0.0, float("nan"), "UNDEFINED_ZERO_SE"
    t = (mx - my) / math.sqrt(se2)
    a, b = vx / len(x), vy / len(y)
    den = a*a/(len(x)-1) + b*b/(len(y)-1)
    df = (a+b)**2/den if den else float("nan")
    return mx, my, vx, vy, math.sqrt(se2), t, "FINITE"

fixed = load_group("fixed")
random = load_group("random")
pcs = sorted(set().union(*(d.keys() for d in fixed + random)))

recomputed = {}
for pc in pcs:
    x = [d.get(pc, 0.0) for d in fixed]
    y = [d.get(pc, 0.0) for d in random]
    mx, my, vx, vy, se, t, status = welch(x, y)
    recomputed[pc] = {
        "PC": pc, "N_FIXED": 10, "N_RANDOM": 10,
        "FIXED_MEAN": mx, "RANDOM_MEAN": my,
        "MEAN_DIFFERENCE_FIXED_MINUS_RANDOM": mx-my,
        "FIXED_VARIANCE": vx, "RANDOM_VARIANCE": vy,
        "STANDARD_ERROR": se, "WELCH_T": t,
        "STATISTIC_STATUS": status,
        "RISK": "HIGH-RISK" if status == "FINITE" and abs(t) > 4.5 else
                ("UNDEFINED" if status != "FINITE" else "NORMAL")
    }

def load_results(path):
    with path.open(newline="") as f:
        return {
            f"0x{int(r['PC'].strip(),16):016x}": r
            for r in csv.DictReader(f)
        }

targets = [
    ("corrected", BASE / "person2_corrected_zero_padded.csv"),
    ("original", BASE / "svs_results.csv"),
]
report = [
    "PERSON 2 — EXACT INPUT RECOMPUTATION",
    "=" * 72,
    f"Fixed runs: {len(fixed)}",
    f"Random runs: {len(random)}",
    f"PC union: {len(pcs)}",
    f"Finite Welch t: {sum(r['STATISTIC_STATUS']=='FINITE' for r in recomputed.values())}",
    f"Undefined zero-SE: {sum(r['STATISTIC_STATUS']!='FINITE' for r in recomputed.values())}",
    f"Finite |t| > 4.5: {sum(r['RISK']=='HIGH-RISK' for r in recomputed.values())}",
]

for label, path in targets:
    report.append(f"\n--- Comparison with {label}: {path} ---")
    if not path.exists():
        report.append("MISSING FILE")
        continue
    existing = load_results(path)
    report.append(f"Rows: {len(existing)}; recomputed rows: {len(recomputed)}")
    report.append(f"PC sets identical: {set(existing) == set(recomputed)}")
    mismatches = []
    for pc in sorted(set(existing) & set(recomputed)):
        a, b = existing[pc], recomputed[pc]
        for field in ("FIXED_MEAN", "RANDOM_MEAN",
                      "FIXED_VARIANCE", "RANDOM_VARIANCE"):
            try:
                av = float(a[field] if field in a else
                           a["FIXED_MEAN_MISSES" if field=="FIXED_MEAN" else
                             "RANDOM_MEAN_MISSES" if field=="RANDOM_MEAN" else
                             "FIXED_VARIANCE" if field=="FIXED_VARIANCE" else
                             "RANDOM_VARIANCE"])
                bv = b[field]
                if not math.isclose(av, bv, rel_tol=1e-7, abs_tol=1e-8):
                    mismatches.append((pc, field, av, bv))
            except (KeyError, ValueError):
                pass
        tfield = "WELCH_T"
        try:
            tv = float(a[tfield])
            rt = b["WELCH_T"]
            if math.isfinite(rt) and not math.isclose(tv, rt, rel_tol=1e-7, abs_tol=1e-8):
                mismatches.append((pc, "WELCH_T", tv, rt))
            if not math.isfinite(rt) and math.isfinite(tv):
                mismatches.append((pc, "WELCH_T", tv, "should be undefined"))
        except (KeyError, ValueError):
            mismatches.append((pc, "WELCH_T", "missing/unreadable", b["WELCH_T"]))
    report.append(f"Field mismatches: {len(mismatches)}")
    for m in mismatches[:20]:
        report.append("MISMATCH " + repr(m))
    if not mismatches and set(existing) == set(recomputed):
        report.append("PASS: compared fields and PC set match.")

# Explicitly show the zero-SE rows
report.append("\n--- Zero-SE cases ---")
for pc, r in recomputed.items():
    if r["STATISTIC_STATUS"] != "FINITE":
        report.append(
            f"{pc}: fixed mean={r['FIXED_MEAN']}, random mean={r['RANDOM_MEAN']}, "
            f"variances={r['FIXED_VARIANCE']}/{r['RANDOM_VARIANCE']}; "
            "Welch t is undefined"
        )

OUT.write_text("\n".join(report) + "\n")
print("\n".join(report))
print(f"\nSaved: {OUT.resolve()}")
