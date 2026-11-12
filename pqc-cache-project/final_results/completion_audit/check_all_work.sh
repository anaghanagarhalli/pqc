#!/usr/bin/env bash

set +e
ROOT="$HOME/pqc-cache-project"
OUT="$ROOT/final_results/completion_audit"
mkdir -p "$OUT"

REPORT="$OUT/PROJECT_COMPLETION_INVENTORY.txt"

{
echo "PERSON 2 — FULL PROJECT COMPLETION INVENTORY"
echo "============================================="
date
echo

echo "1. PROJECT STRUCTURE"
find "$ROOT" -maxdepth 3 -type d | sort
echo

echo "2. EXPERIMENT AND ANALYSIS SCRIPTS"
find "$ROOT" -type f \( \
  -name "*.py" -o -name "*.sh" -o -name "*.tcl" \
\) | sort
echo

echo "3. RISC-V ELF FILES"
find "$ROOT" -type f -name "*.elf" | sort
echo

echo "4. TRACE CSV FILES"
find "$ROOT" -type f -name "trace_*.csv" | sort
echo

echo "TRACE COUNTS"
echo -n "Fixed traces: "
find "$ROOT" -type f -path "*/runs/fixed/trace_*.csv" | wc -l
echo -n "Random traces: "
find "$ROOT" -type f -path "*/runs/random/trace_*.csv" | wc -l
echo

echo "5. WR1 ARTIFACTS"
find "$ROOT" -type f | grep -Ei 'WR1|phase4_cache|high_risk_source_mapping|misses_' || true
echo

echo "6. WR2 ARTIFACTS"
find "$ROOT" -type f | grep -Ei 'WR2|phase5_svc|welch|confidence|person2' || true
echo

echo "7. WR3 ARTIFACTS"
find "$ROOT" -type f | grep -Ei 'WR3|svs|side.channel|vulnerability' || true
echo

echo "8. PROVENANCE AND BUILD RECORDS"
find "$ROOT" -type f \( \
  -iname "*manifest*" -o \
  -iname "*provenance*" -o \
  -iname "*build*.log" -o \
  -iname "*run*.log" -o \
  -iname "*config*" \
\) | sort
echo

echo "9. AVAILABLE TOOL VERSIONS"
command -v spike && spike --version 2>&1 | head -n 2
command -v riscv64-unknown-elf-gcc && riscv64-unknown-elf-gcc --version | head -n 1
command -v python3 && python3 --version

echo
echo "10. CURRENT COMPLETION STATUS"
echo "WR1: Requires complete experiment sweep and supporting run evidence."
echo "WR2: Reconstructed analysis exists; original seeds/provenance need verification."
echo "WR3: Existing artifacts found; original experiment runner and evidence need verification."
echo "C5: Requires primary experiment source, procedure and raw results."
echo "C9: Requires trace-to-ELF provenance records."
echo
echo "This inventory does not claim that missing experiments were executed."
} > "$REPORT"

echo "INVENTORY CREATED:"
echo "$REPORT"
echo
cat "$REPORT"
