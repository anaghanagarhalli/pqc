import os, csv, hashlib, glob, re, math
from pathlib import Path
from collections import Counter

ROOT = Path.cwd()
PROJECT = ROOT.parent
OUT = ROOT / "PERSON2_VERIFICATION_AUDIT.txt"
lines = []

def log(s=""):
    lines.append(str(s))
    print(s)

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

log("=" * 76)
log("PERSON 2 — FINAL EVIDENCE VERIFICATION")
log("=" * 76)
log(f"Working directory: {ROOT}")
log(f"Project directory: {PROJECT}")
log()

# 1. Verify expected deliverables
log("1. EXPECTED DELIVERABLES")
expected = [
    "person2_corrected_zero_padded.csv",
    "person2_pc_source_mapping.csv",
    "person2_findings_summary.txt",
    "person2_final_audit.txt",
    "person2_final_elf_mapping.txt",
    "person2_C5_C9_final_audit.txt",
    "person2_C5_C9_provenance_check.txt",
    "person2_completion_report.txt",
    "PERSON2_FINAL_STATUS.txt",
]
for name in expected:
    p = ROOT / name
    log(f"{'PRESENT' if p.is_file() else 'MISSING'}: {name}"
        + (f" ({p.stat().st_size} bytes)" if p.is_file() else ""))

# 2. Locate experiment data, scripts, logs and ELFs
log()
log("2. EXPERIMENT ARTIFACT INVENTORY")
patterns = [
    "**/misses_*.csv", "**/*svs*analysis*.py", "**/*tvla*.py",
    "**/*experiment*.py", "**/*run*.sh", "**/*test*.log",
    "**/*timing*.csv", "**/*trace*.csv", "**/*result*.csv",
    "**/*summary*.txt", "**/*.elf", "**/*.map", "**/*.dump",
]
found = {}
for base in [ROOT, PROJECT]:
    for pat in patterns:
        try:
            for p in base.glob(pat):
                if p.is_file():
                    try:
                        rel = str(p.relative_to(PROJECT))
                    except ValueError:
                        rel = str(p)
                    found[rel] = p
        except (OSError, PermissionError):
            pass

for name in sorted(found):
    p = found[name]
    log(f"{name} | {p.stat().st_size} bytes")

# 3. Inspect the actual miss CSV families and their headers
log()
log("3. MISS CSV DATASET CHECK")
miss_files = [p for p in found.values()
              if re.fullmatch(r"misses_\d+\.csv", p.name)]
if not miss_files:
    log("NO misses_N.csv files found in searched directories.")
for p in sorted(miss_files, key=lambda x: (str(x.parent), x.name)):
    try:
        with p.open(newline="", errors="replace") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            log(f"\nFILE: {p}")
            log(f"Header: {reader.fieldnames}")
            log(f"Data rows: {len(rows)}")
            for r in rows[:2]:
                log(f"Sample: {r}")
    except Exception as e:
        log(f"ERROR reading {p}: {e}")

# Check expected zero-padded paired data explicitly
log()
log("4. ZERO-PADDED INPUT COMPLETENESS")
for group in ["fixed", "random"]:
    d = ROOT / "runs" / group
    present = []
    missing = []
    for i in range(1, 11):
        p = d / f"misses_{i:02d}.csv"
        (present if p.is_file() else missing).append(p.name)
    log(f"{group}: {len(present)}/10 present")
    if missing:
        log("  Missing: " + ", ".join(missing))

# 5. Independently inspect corrected CSV and flag zero-SE cases
log()
log("5. CORRECTED RESULT CSV SANITY CHECK")
corrected = ROOT / "person2_corrected_zero_padded.csv"
if corrected.is_file():
    try:
        with corrected.open(newline="", errors="replace") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            log(f"Rows: {len(rows)}")
            log(f"Columns: {reader.fieldnames}")
            for r in rows[:3]:
                log(f"Sample: {r}")
            log("Inspect the columns above for t-statistic, variance, sample-size, "
                "and classification fields.")
    except Exception as e:
        log(f"ERROR: {e}")
else:
    log("Corrected CSV is missing; cannot verify classifications.")

# 6. ELF provenance: hashes and debug information
log()
log("6. ELF IDENTITY AND DEBUG INFORMATION")
elfs = [p for p in found.values() if p.suffix == ".elf"]
hash_groups = {}
for p in sorted(elfs):
    digest = sha256(p)
    hash_groups.setdefault(digest, []).append(str(p))
    log(f"{p} | SHA256 {digest} | modified {p.stat().st_mtime}")
log("\nIdentical-hash groups:")
for digest, members in hash_groups.items():
    if len(members) > 1:
        log(f"{digest}: " + " == ".join(members))
if not elfs:
    log("No ELF binaries found.")

# 7. Search available scripts/reports for provenance clues
log()
log("7. PROVENANCE AND WORKFLOW REFERENCES")
terms = re.compile(
    r"misses_01|misses_1\.csv|phase5_fixed|phase5_random|"
    r"LEAKY|504.configuration|100 fixed|100 random|"
    r"Welch|t.statistic|high.risk|trace|ELF|objdump|addr2line",
    re.I
)
extensions = {".py", ".sh", ".txt", ".md", ".log", ".csv", ".json", ".yaml", ".yml"}
count = 0
for base in [ROOT, PROJECT]:
    for p in base.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in extensions:
            continue
        if any(part in {".git", "__pycache__", ".venv", "venv"} for part in p.parts):
            continue
        try:
            if p.stat().st_size > 5_000_000:
                continue
            with p.open("r", errors="replace") as f:
                matches = []
                for n, line in enumerate(f, 1):
                    if terms.search(line):
                        matches.append((n, line.strip()[:240]))
                        if len(matches) >= 4:
                            break
            if matches:
                log(f"\n{p}")
                for n, line in matches:
                    log(f"  L{n}: {line}")
                count += 1
                if count >= 100:
                    log("Stopped after 100 matching files.")
                    break
        except (OSError, PermissionError, UnicodeDecodeError):
            pass
    if count >= 100:
        break

# 8. Available toolchain
log()
log("8. TOOLCHAIN")
for cmd in ["python3", "riscv64-unknown-elf-objdump",
            "riscv64-unknown-elf-addr2line", "riscv64-unknown-elf-readelf"]:
    import shutil
    log(f"{cmd}: {shutil.which(cmd) or 'NOT FOUND'}")

# 9. Existing final status and report tails
log()
log("9. CURRENT STATUS FILE CONTENTS")
for name in ["PERSON2_FINAL_STATUS.txt", "person2_completion_report.txt",
             "person2_C5_C9_provenance_check.txt"]:
    p = ROOT / name
    if p.is_file():
        log(f"\n--- {name} (last 35 lines) ---")
        try:
            content = p.read_text(errors="replace").splitlines()
            for line in content[-35:]:
                log(line[:300])
        except Exception as e:
            log(f"Could not read: {e}")

log()
log("=" * 76)
log("AUDIT COMPLETE — THIS SCRIPT DOES NOT CLAIM EXPERIMENTAL VALIDATION "
    "SOLELY FROM FILE EXISTENCE.")
log("Review missing inputs, dataset separation, and exact ELF-to-trace provenance.")
log("=" * 76)

OUT.write_text("\n".join(lines) + "\n")
print(f"\nAudit saved to: {OUT}")
