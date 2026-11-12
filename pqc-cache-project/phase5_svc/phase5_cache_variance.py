#!/usr/bin/env python3

import argparse
import csv
import random
from pathlib import Path

from importlib.util import spec_from_file_location, module_from_spec

SIM_PATH = Path.home() / "pqc-cache-project/phase4_cache/cache_simulator.py"

spec = spec_from_file_location("cache_simulator", SIM_PATH)
mod = module_from_spec(spec)
spec.loader.exec_module(mod)

def read_trace(path):
    rows = []
    blocks = []

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pc = int(row["PC"], 16)
            access_type = row["ACCESS"].strip().upper()
            address = int(row["ADDRESS"], 16)
            size = int(row["SIZE"])
            rows.append((pc, access_type, address, size))
            blocks.append(address // 32)

    return rows, sorted(set(blocks))

def run(trace_path, seed, output_path):
    rows, blocks = read_trace(trace_path)

    sim = mod.CacheSimulator(
        cache_size=8 * 1024,
        associativity=4,
        block_size=32,
        policy="Pseudo-LRU",
    )

    rng = random.Random(seed)

    # Model a variable cache state before the measured cryptographic run.
    # Half of the cache lines are pre-populated with blocks drawn from the
    # trace's working set. This is initialization state, not crypto data.
    prefill_count = min(128, len(blocks))
    for block in rng.sample(blocks, prefill_count):
        sim.access(block * 32, "READ")

    misses_by_pc = {}

    for pc, access_type, address, size in rows:
        result = sim.access(address, access_type)
        if not result["hit"]:
            misses_by_pc[pc] = misses_by_pc.get(pc, 0) + 1

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["PC", "MISSES"])
        for pc in sorted(misses_by_pc):
            w.writerow([f"{pc:016x}", misses_by_pc[pc]])

    return sim.hits, sim.misses

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace", required=True)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    hits, misses = run(args.trace, args.seed, args.output)
    print(f"Hits={hits} Misses={misses}")

if __name__ == "__main__":
    main()
