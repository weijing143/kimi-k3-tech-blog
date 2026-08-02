#!/usr/bin/env python3
"""Validate data/benchmarks.json integrity.

Checks:
  1. JSON parses
  2. benchmark count matches meta.count (31)
  3. names unique
  4. category values in allowed set
  5. required fields present (name, category, score)
  6. score is numeric or null; unit in {null, "Elo", "F1"}

Usage: python3 scripts/check_benchmarks.py [path]
"""
import json
import sys

ALLOWED_CATEGORIES = {
    "coding", "info-gathering", "tool-use", "productivity",
    "agent", "reasoning", "multimodal",
}
REQUIRED_FIELDS = ("name", "category", "score")
ALLOWED_UNITS = (None, "Elo", "F1")


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else "data/benchmarks.json"
    errors = []

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"FAIL: cannot load {path}: {e}")
        return 1

    meta = data.get("meta", {})
    benchs = data.get("benchmarks", [])

    # 1. count
    declared = meta.get("count")
    if declared is None:
        errors.append("meta.count missing")
    elif len(benchs) != declared:
        errors.append(f"meta.count={declared} but benchmarks array has {len(benchs)}")

    # 2. required fields + 3. uniqueness + 4. category + 5. score type
    seen = set()
    for i, b in enumerate(benchs):
        for f in REQUIRED_FIELDS:
            if f not in b:
                errors.append(f"benchmarks[{i}] missing field '{f}'")
                continue
        name = b.get("name")
        if name in seen:
            errors.append(f"duplicate benchmark name: {name}")
        seen.add(name)
        cat = b.get("category")
        if cat not in ALLOWED_CATEGORIES:
            errors.append(f"benchmarks[{i}] invalid category: {cat!r}")
        sc = b.get("score")
        if sc is not None and not isinstance(sc, (int, float)):
            errors.append(f"benchmarks[{i}] score must be number or null, got {sc!r}")
        unit = b.get("unit")
        if unit not in ALLOWED_UNITS:
            errors.append(f"benchmarks[{i}] invalid unit: {unit!r}")

    # 6. report
    if errors:
        print(f"FAIL ({len(errors)} issue(s)):")
        for e in errors:
            print(f"  - {e}")
        return 1

    cats = {}
    for b in benchs:
        cats[b["category"]] = cats.get(b["category"], 0) + 1
    print(f"OK: {len(benchs)} benchmarks, {len(seen)} unique names")
    print("  categories: " + ", ".join(f"{k}={v}" for k, v in sorted(cats.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
