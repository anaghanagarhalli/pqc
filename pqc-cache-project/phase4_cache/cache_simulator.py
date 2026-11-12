#!/usr/bin/env python3

import argparse
import random
from dataclasses import dataclass


@dataclass
class CacheLine:
    valid: bool = False
    tag: int = 0
class CacheSet:
    def __init__(self, associativity: int, policy: str):
        self.lines = [CacheLine() for _ in range(associativity)]
        self.policy = policy
        self.associativity = associativity

        # LRU ordering: index 0 = least recently used
        self.lru_order = list(range(associativity))

        # Tree-based Pseudo-LRU.
        # For N ways, N-1 bits are used.
        # 0 = left subtree is least recently used
        # 1 = right subtree is least recently used
        self.plru_bits = [0] * max(0, associativity - 1)

    def find_tag(self, tag: int) -> int | None:
        for way, line in enumerate(self.lines):
            if line.valid and line.tag == tag:
                return way
        return None

    def choose_victim(self) -> int:
        for way, line in enumerate(self.lines):
            if not line.valid:
                return way

        if self.policy == "LRU":
            return self.lru_order[0]

        if self.policy == "Random":
            return random.randrange(len(self.lines))

        # Tree-based Pseudo-LRU
        if self.associativity == 1:
            return 0

        node = 0
        way = 0
        remaining = self.associativity

        while remaining > 1:
            half = remaining // 2

            if self.plru_bits[node] == 0:
                # Left subtree is least recently used.
                node = 2 * node + 1
            else:
                # Right subtree is least recently used.
                way += half
                node = 2 * node + 2

            remaining = half

        return way

    def update_replacement_state(self, way: int) -> None:
        if self.policy == "LRU":
            if way in self.lru_order:
                self.lru_order.remove(way)
            self.lru_order.append(way)

        elif self.policy == "Pseudo-LRU":
            if self.associativity > 1:
                node = 0
                remaining = self.associativity
                offset = way

                while remaining > 1:
                    half = remaining // 2

                    if offset < half:
                        # Accessed left subtree, so right becomes LRU.
                        self.plru_bits[node] = 1
                        node = 2 * node + 1
                    else:
                        # Accessed right subtree, so left becomes LRU.
                        self.plru_bits[node] = 0
                        node = 2 * node + 2
                        offset -= half

                    remaining = half

        # Random policy does not maintain replacement state.

class CacheSimulator:
    def __init__(
        self,
        cache_size: int,
        associativity: int,
        block_size: int,
        policy: str,
    ):
        self.cache_size = cache_size
        self.associativity = associativity
        self.block_size = block_size
        self.policy = policy

        total_lines = cache_size // block_size

        if total_lines % associativity != 0:
            raise ValueError(
                "Cache size must produce an integer number of sets."
            )

        self.num_sets = total_lines // associativity

        self.sets = [
            CacheSet(associativity, policy)
            for _ in range(self.num_sets)
        ]

        self.hits = 0
        self.misses = 0
        self.reads = 0
        self.writes = 0
        self.misses_by_pc = {}

    def access(self, address: int, access_type: str):
        block_address = address // self.block_size
        set_index = block_address % self.num_sets
        tag = block_address // self.num_sets

        cache_set = self.sets[set_index]
        hit_way = cache_set.find_tag(tag)

        if access_type == "READ":
            self.reads += 1
        elif access_type == "WRITE":
            self.writes += 1

        if hit_way is not None:
            self.hits += 1
            cache_set.update_replacement_state(hit_way)
            return {
                "hit": True,
                "set_index": set_index,
                "tag": tag,
                "way": hit_way,
            }

        self.misses += 1

        victim_way = cache_set.choose_victim()
        cache_set.lines[victim_way].valid = True
        cache_set.lines[victim_way].tag = tag
        cache_set.update_replacement_state(victim_way)

        return {
            "hit": False,
            "set_index": set_index,
            "tag": tag,
            "way": victim_way,
        }

    def process_trace(self, trace_file: str, output_file: str | None = None):
        with open(trace_file, "r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                line = line.strip()

                if not line:
                    continue

                if line_number == 1:
                    continue

                parts = line.split(",")

                if len(parts) != 4:
                    raise ValueError(
                        f"Invalid trace line {line_number}: {line}"
                    )

                pc_text, access_type, address_text, size_text = parts
                pc = int(pc_text.strip(), 16)

                access_type = access_type.strip().upper()
                address = int(address_text.strip(), 16)
                size = int(size_text.strip())

                result = self.access(address, access_type)

                if not result["hit"]:
                    self.misses_by_pc[pc] = self.misses_by_pc.get(pc, 0) + 1

                # Parsed for trace correctness and future extensions.
                _ = size
                _ = result

    def write_miss_distribution(self, output_file: str) -> None:
        with open(output_file, "w", encoding="utf-8") as file:
            file.write("PC,MISSES\n")
            for pc in sorted(self.misses_by_pc):
                file.write(f"{pc:016x},{self.misses_by_pc[pc]}\n")

    def summary(self) -> None:
        total = self.hits + self.misses

        hit_rate = (self.hits / total * 100) if total else 0.0
        miss_rate = (self.misses / total * 100) if total else 0.0

        print(f"Cache size      : {self.cache_size // 1024} KB")
        print(f"Associativity   : {self.associativity}-way")
        print(f"Block size      : {self.block_size} bytes")
        print(f"Policy          : {self.policy}")
        print(f"Sets            : {self.num_sets}")
        print(f"Reads           : {self.reads}")
        print(f"Writes          : {self.writes}")
        print(f"Hits            : {self.hits}")
        print(f"Misses          : {self.misses}")
        print(f"Hit rate        : {hit_rate:.4f}%")
        print(f"Miss rate       : {miss_rate:.4f}%")


def parse_associativity(value: str) -> int:
    value = value.lower()

    mapping = {
        "direct": 1,
        "dm": 1,
        "1": 1,
        "2": 2,
        "4": 4,
        "8": 8,
    }

    if value not in mapping:
        raise argparse.ArgumentTypeError(
            "Associativity must be direct, 2, 4, or 8."
        )

    return mapping[value]


def parse_policy(value: str) -> str:
    normalized = value.lower()

    mapping = {
        "lru": "LRU",
        "pseudo-lru": "Pseudo-LRU",
        "plru": "Pseudo-LRU",
        "random": "Random",
    }

    if normalized not in mapping:
        raise argparse.ArgumentTypeError(
            "Policy must be LRU, Pseudo-LRU, or Random."
        )

    return mapping[normalized]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Event-driven Python L1 Data Cache Simulator"
    )

    parser.add_argument(
        "--trace",
        required=True,
        help="Path to Spike CSV trace file",
    )

    parser.add_argument(
        "--cache-size",
        type=int,
        choices=[8, 16, 32],
        required=True,
        help="Cache size in KB",
    )

    parser.add_argument(
        "--associativity",
        type=parse_associativity,
        required=True,
        help="direct, 2, 4, or 8",
    )

    parser.add_argument(
        "--block-size",
        type=int,
        choices=[32, 64],
        required=True,
        help="Cache block size in bytes",
    )

    parser.add_argument(
        "--miss-output",
        help="Optional CSV file for per-instruction cache misses",
    )

    parser.add_argument(
        "--policy",
        type=parse_policy,
        required=True,
        help="LRU, Pseudo-LRU, or Random",
    )

    args = parser.parse_args()

    simulator = CacheSimulator(
        cache_size=args.cache_size * 1024,
        associativity=args.associativity,
        block_size=args.block_size,
        policy=args.policy,
    )

    simulator.process_trace(args.trace, args.miss_output)
    if args.miss_output:
        simulator.write_miss_distribution(args.miss_output)
    simulator.summary()


if __name__ == "__main__":
    main()
