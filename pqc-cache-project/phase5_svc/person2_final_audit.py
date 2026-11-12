import csv
import math
import subprocess
from pathlib import Path
from datetime import datetime

base = Path.home() / "pqc-cache-project"
phase = base / "phase5_svc"
out = phase / "person2_final_audit.txt"
pcs = [
    0x80000474, 0x80000484, 0x80000494, 0x800004a4,
    0x80000520, 0x80000540, 0x8000055c, 0x80000560,
    0x8000057c, 0x80000580, 0x800005b6, 0x800005bc,
    0x800005d6
]
lines = []
def log(s=""):
    lines.append(str(s))
def read_csv(p):
    with open(p, newline="") as f:
        return list(csv.DictReader(f))

log("PERSON 2 FINAL AUDIT")
log("Generated: " + datetime.now().isoformat(timespec="seconds"))
log("=" * 65)

# 1. Statistical outputs and CI review
log("\n1. STATISTICAL OUTPUTS")
for name in ("person2_corrected_zero_padded.csv",
             "person2_corrected_full_runs.csv"):
    p = phase / name
    if not p.exists():
        log(f"{name}: MISSING")
        continue
    rows = read_csv(p)
    high = [r for r in rows if r.get("RISK") == "HIGH-RISK"]
    undef = [r for r in rows if r.get("RISK") == "UNDEFINED"]
    log(f"{name}: {len(rows)} PCs; finite high-risk={len(high)}; "
        f"undefined={len(undef)}")
    log("  Confidence intervals: review column names and calculation before publication.")
    log("  Zero SE rows are undefined; do not interpret their t-statistics as infinity.")

# Verify current data file families and counts
log("\n2. INPUT FILE PROVENANCE")
for group in ("fixed", "random"):
    folder = phase / "runs" / group
    log(f"{group}:")
    for pattern in ("misses_[0-9][0-9].csv", "misses_[0-9].csv"):
        files = sorted(folder.glob(pattern))
        log(f"  {pattern}: {len(files)} files")
        if files:
            log("    " + ", ".join(x.name for x in files))
log("The zero-padded and non-zero-padded datasets are separate and must not be pooled.")

# 3. Map the 13 original flagged PCs against multiple candidate ELFs
log("\n3. ELF / SOURCE MAPPING CROSS-CHECK")
elfs = [phase / n for n in ("phase5_fixed.elf", "phase5_test_fixed.elf",
                             "phase5_fixed_1.elf")]
mapping = phase / "person2_final_elf_mapping.txt"
with open(mapping, "w") as mf:
    for elf in elfs:
        mf.write(f"\n===== {elf.name} =====\n")
        if not elf.exists():
            mf.write("ELF NOT FOUND\n")
            continue
        for pc in pcs:
            proc = subprocess.run(
                ["riscv64-unknown-elf-addr2line", "-f", "-C", "-i",
                 "-e", str(elf), hex(pc)],
                capture_output=True, text=True
            )
            mf.write(f"\nPC 0x{pc:016x}\n")
            mf.write(proc.stdout.strip() or proc.stderr.strip())
            mf.write("\n")
log(f"Created mapping comparison: {mapping}")
log("Important: addr2line output is only valid for the ELF that generated the measured traces.")
log("Confirming which ELF generated each run is required before final publication.")

# 4. Search stored textual evidence for the three experimental workflows
log("\n4. WORKFLOW EVIDENCE INVENTORY")
keywords = ("LEAKY", "504", "configuration", "baseline", "lookup",
            "branch", "6857", "7114", "7421", "TVLA", "Welch",
            "high-risk", "source mapping")
found = 0
for folder in (base / "phase1", base / "phase2", base / "phase3",
               base / "phase4_cache", phase, base / "phase6"):
    if not folder.exists():
        continue
    for p in folder.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in (".txt", ".csv", ".log", ".md"):
            continue
        try:
            if p.stat().st_size > 5_000_000:
                continue
            text = p.read_text(errors="ignore")
        except Exception:
            continue
        matches = [k for k in keywords if k.lower() in text.lower()]
        if matches:
            log(f"{p}: {', '.join(matches[:8])}")
            found += 1
            if found >= 60:
                log("Search output capped at 60 matching files.")
                break
    if found >= 60:
        break
if found == 0:
    log("No matching textual evidence found in the searched folders.")

log("\n5. THREE WORKFLOWS — RECONCILIATION STATUS")
log("Workflow A: broad configuration sweep — earlier reported result: six crypto kernels")
log("  had zero flagged locations, while the LEAKY positive control was detected.")
log("Workflow B: per-PC cache-miss experiment — the zero-padded dataset has 194 PCs;")
log("  its corrected output has 10 finite threshold exceedances and 3 undefined rows.")
log("Workflow C: separate timing experiment — earlier reported baseline means were equal;")
log("  lookup had unequal means but zero variance; branch injection showed a timing difference.")
log("These are different experiments and metrics. They must be described separately.")
log("The figures above are prior reported results; verify them against original logs before publication.")

log("\n6. REQUIRED FINAL CHECKS")
log("- Use only finite Welch t-statistics for threshold classification.")
log("- For zero standard error, report t as undefined and give group means/variances.")
log("- Check that confidence intervals use an appropriate Welch t critical value for each df.")
log("- Do not present the existing approximate intervals as exact.")
log("- Match every mapped PC to the ELF used for its measured run.")
log("- Support each workflow's claims with its own stored logs/results.")
log("\nAudit generated. Original runs, analysis script, and original results CSV were not changed.")

out.write_text("\n".join(lines) + "\n")
print("\n".join(lines))
print(f"\nSaved full audit: {out}")
print(f"Saved ELF comparison: {mapping}")
