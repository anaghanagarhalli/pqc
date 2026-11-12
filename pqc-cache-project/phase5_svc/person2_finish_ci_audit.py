import csv, math, statistics
from pathlib import Path

root = Path(".")
folder = root / "person2_rebuilt_full"
source = folder / "person2_full_trace_welch_results.csv"
output = folder / "person2_full_trace_with_ci.csv"
report = folder / "PERSON2_CI_AUDIT.txt"

if not source.exists():
    raise SystemExit(f"Missing input: {source}")

# Welch-Satterthwaite df and approximate 95% CI.
# Critical values use a normal approximation; intervals are labelled approximate.
def critical(df):
    # Conservative two-sided 95% t critical approximation for moderate/large df.
    if not math.isfinite(df) or df <= 0:
        return float("nan")
    z = 1.959964
    return z + (z**3 + z)/(4*df) + (5*z**5 + 16*z**3 + 3*z)/(96*df**2)

with source.open(newline="") as f:
    rows = list(csv.DictReader(f))

count_ci = count_undefined = 0
with output.open("w", newline="") as f:
    fields = list(rows[0].keys()) + [
        "mean_difference_fixed_minus_random", "welch_se",
        "ci95_lower_approx", "ci95_upper_approx", "ci_status"
    ]
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()

    for r in rows:
        try:
            a = float(r["fixed_mean"])
            b = float(r["random_mean"])
            va = float(r["fixed_variance"])
            vb = float(r["random_variance"])
            n1 = n2 = 10
            se2 = va/n1 + vb/n2
            diff = a-b
            if not all(math.isfinite(x) for x in (a,b,va,vb)) or se2 <= 0:
                raise ValueError("non-finite values or zero standard error")
            se = math.sqrt(se2)
            x, y = va/n1, vb/n2
            denom = x*x/(n1-1) + y*y/(n2-1)
            df = (x+y)**2/denom if denom > 0 else float("nan")
            crit = critical(df)
            if not math.isfinite(crit):
                raise ValueError("invalid degrees of freedom")
            r["mean_difference_fixed_minus_random"] = f"{diff:.10g}"
            r["welch_se"] = f"{se:.10g}"
            r["ci95_lower_approx"] = f"{diff-crit*se:.10g}"
            r["ci95_upper_approx"] = f"{diff+crit*se:.10g}"
            r["ci_status"] = "APPROXIMATE_95_PERCENT"
            count_ci += 1
        except (ValueError, KeyError, ZeroDivisionError):
            r["mean_difference_fixed_minus_random"] = ""
            r["welch_se"] = ""
            r["ci95_lower_approx"] = ""
            r["ci95_upper_approx"] = ""
            r["ci_status"] = "UNDEFINED"
            count_undefined += 1
        w.writerow(r)

report.write_text(
    "PERSON 2 — RECONSTRUCTED CONFIDENCE INTERVAL AUDIT\n"
    "=================================================\n"
    f"Input: {source}\n"
    f"Rows processed: {len(rows)}\n"
    f"Approximate 95% intervals computed: {count_ci}\n"
    f"Undefined intervals: {count_undefined}\n\n"
    "Method: Welch standard error and Welch-Satterthwaite degrees of freedom.\n"
    "Critical values use a t-critical approximation; intervals are approximate.\n"
    "These intervals use reconstructed data and newly assigned cache-prefill seeds.\n"
    "They do not validate original experimental results or ELF-to-trace provenance.\n"
    "Original files were not overwritten.\n"
)
print(report.read_text())
print("CSV saved:", output.resolve())
print("Audit saved:", report.resolve())
