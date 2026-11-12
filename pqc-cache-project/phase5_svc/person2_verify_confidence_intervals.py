import csv, math
from pathlib import Path

src = Path("person2_corrected_zero_padded.csv")
out = Path("person2_corrected_exact_ci.csv")
report = Path("PERSON2_CI_VERIFICATION.txt")

def beta_cf(a, b, x):
    qab, qap, qam = a+b, a+1, a-1
    c, d = 1.0, 1.0-qab*x/qap
    d = 1.0/(d if abs(d) > 1e-300 else 1e-300)
    h = d
    for m in range(1, 501):
        m2 = 2*m
        aa = m*(b-m)*x/((qam+m2)*(a+m2))
        d = 1+aa*d
        d = d if abs(d)>1e-300 else 1e-300
        c = 1+aa/c
        c = c if abs(c)>1e-300 else 1e-300
        d = 1/d
        h *= d*c
        aa = -(a+m)*(qab+m)*x/((a+m2)*(qap+m2))
        d = 1+aa*d
        d = d if abs(d)>1e-300 else 1e-300
        c = 1+aa/c
        c = c if abs(c)>1e-300 else 1e-300
        d = 1/d
        delta = d*c
        h *= delta
        if abs(delta-1) < 3e-14:
            break
    return h

def ibeta(a, b, x):
    if x <= 0: return 0.0
    if x >= 1: return 1.0
    front = math.exp(math.lgamma(a+b)-math.lgamma(a)-math.lgamma(b)
                     + a*math.log(x)+b*math.log1p(-x))
    if x < (a+1)/(a+b+2):
        return front*beta_cf(a,b,x)/a
    return 1-front*beta_cf(b,a,1-x)/b

def tcdf(t, df):
    if t == 0: return 0.5
    tail = 0.5*ibeta(df/2, 0.5, df/(df+t*t))
    return 1-tail if t > 0 else tail

def tcrit(df):
    lo, hi = 0.0, 100.0
    for _ in range(100):
        mid = (lo+hi)/2
        if tcdf(mid, df) < 0.975: lo = mid
        else: hi = mid
    return (lo+hi)/2

if not src.exists():
    raise SystemExit(f"Missing input: {src}")

with src.open(newline="") as f:
    rows = list(csv.DictReader(f))
if not rows:
    raise SystemExit("Input CSV has no data rows.")

fields = list(rows[0])
for name in ("CI95_LOW_EXACT", "CI95_HIGH_EXACT", "CI95_STATUS"):
    if name not in fields:
        fields.append(name)

mismatches, undefined = [], 0

for r in rows:
    diff = float(r["MEAN_DIFFERENCE_FIXED_MINUS_RANDOM"])
    se = float(r["STANDARD_ERROR"])
    df = float(r["WELCH_DF"])

    if se == 0 or not math.isfinite(df) or df <= 0:
        low = high = float("nan")
        status = "UNDEFINED_ZERO_SE_OR_DF"
        undefined += 1
    else:
        crit = tcrit(df)
        low, high = diff-crit*se, diff+crit*se
        status = "WELCH_T_95_PERCENT_INTERVAL"
        try:
            old_low = float(r["CI95_LOW_APPROX"])
            old_high = float(r["CI95_HIGH_APPROX"])
            if (not math.isclose(old_low, low, rel_tol=1e-5, abs_tol=1e-5)
                or not math.isclose(old_high, high, rel_tol=1e-5, abs_tol=1e-5)):
                mismatches.append(r["PC"])
        except (KeyError, ValueError):
            pass

    r["CI95_LOW_EXACT"] = f"{low:.10g}" if math.isfinite(low) else "NA"
    r["CI95_HIGH_EXACT"] = f"{high:.10g}" if math.isfinite(high) else "NA"
    r["CI95_STATUS"] = status

with out.open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

lines = [
    "PERSON 2 — WELCH CONFIDENCE INTERVAL VERIFICATION",
    f"Rows processed: {len(rows)}",
    f"Approximate intervals differing from recomputed Welch intervals: {len(mismatches)}",
    f"Undefined intervals (zero SE or invalid df): {undefined}",
    f"Output CSV: {out}",
    "The original corrected CSV was preserved."
]
if mismatches:
    lines.append("First differing PCs: " + ", ".join(mismatches[:20]))
report.write_text("\n".join(lines) + "\n")
print("\n".join(lines))
print(f"Report saved: {report.resolve()}")
print(f"CSV saved: {out.resolve()}")
