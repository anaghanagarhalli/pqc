#!/usr/bin/env python3

import argparse
import re
import subprocess
import sys


def run_cache_simulator(simulator, trace, cache_size, associativity,
                        block_size, policy):
    cmd = [
        sys.executable, simulator,
        "--trace", trace,
        "--cache-size", str(cache_size),
        "--associativity", associativity,
        "--block-size", str(block_size),
        "--policy", policy,
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=True
    )

    output = result.stdout

    hits_match = re.search(r"Hits\s*:\s*(\d+)", output)
    misses_match = re.search(r"Misses\s*:\s*(\d+)", output)

    if not hits_match or not misses_match:
        raise RuntimeError(
            "Could not extract Hits/Misses from cache simulator output."
        )

    hits = int(hits_match.group(1))
    misses = int(misses_match.group(1))

    return output, hits, misses


def main():
    parser = argparse.ArgumentParser(
        description="Add cycle/latency modeling to the L1 cache simulator."
    )

    parser.add_argument("--trace", required=True)
    parser.add_argument("--cache-size", type=int, default=8)
    parser.add_argument(
        "--associativity",
        choices=["direct", "2", "4", "8"],
        default="4"
    )
    parser.add_argument("--block-size", type=int, default=32)
    parser.add_argument(
        "--policy",
        choices=["LRU", "Pseudo-LRU", "Random"],
        default="Pseudo-LRU"
    )

    parser.add_argument(
        "--hit-latency",
        type=float,
        default=1.0,
        help="Hit latency in cycles (default: 1)"
    )
    parser.add_argument(
        "--miss-penalty",
        type=float,
        default=50.0,
        help="Total miss latency in cycles (default: 50)"
    )
    parser.add_argument(
        "--frequency-ghz",
        type=float,
        default=1.0,
        help="CPU frequency in GHz (default: 1.0)"
    )

    args = parser.parse_args()

    simulator = "cache_simulator.py"

    output, hits, misses = run_cache_simulator(
        simulator,
        args.trace,
        args.cache_size,
        args.associativity,
        args.block_size,
        args.policy
    )

    total_accesses = hits + misses

    total_cycles = (
        hits * args.hit_latency
        + misses * args.miss_penalty
    )

    execution_time_ns = total_cycles / args.frequency_ghz

    print(output.rstrip())
    print()
    print("----- LATENCY / EXECUTION-TIME MODEL -----")
    print(f"Hit latency          : {args.hit_latency:g} cycles")
    print(f"Miss penalty         : {args.miss_penalty:g} cycles")
    print(f"CPU frequency        : {args.frequency_ghz:g} GHz")
    print(f"Total accesses       : {total_accesses}")
    print(f"Total cycles         : {total_cycles:g}")
    print(f"Estimated time       : {execution_time_ns:g} ns")
    print(f"Estimated time       : {execution_time_ns / 1000:g} us")


if __name__ == "__main__":
    main()
