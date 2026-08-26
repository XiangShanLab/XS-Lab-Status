#!/usr/bin/env python3
"""Generate a README leaderboard from ledger/score-log.md.

The first version only reads a simple markdown table and emits a compact table
for manual copy or future automation.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path


def parse_table(path: Path):
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = []
    for line in lines:
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        rows.append(cells)
    if len(rows) < 2:
        return []
    header = rows[0]
    data = rows[2:] if len(rows) > 2 else []
    return [dict(zip(header, row)) for row in data if len(row) == len(header)]


def main() -> int:
    ledger = Path("ledger/score-log.md")
    rows = parse_table(ledger)
    score = defaultdict(float)
    events = defaultdict(int)
    for row in rows:
        actor = row.get("Actor", "")
        try:
            delta = float(row.get("Delta", "0"))
        except ValueError:
            delta = 0.0
        score[actor] += delta
        if row.get("Type") in {"reward", "penalty"}:
            events[actor] += 1

    print("| Member | Score | Events |")
    print("| --- | ---: | ---: |")
    for actor, value in sorted(score.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"| {actor} | {value:.1f} | {events[actor]} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
