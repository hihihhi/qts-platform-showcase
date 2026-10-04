#!/usr/bin/env python3
"""Read the figures out of docs/results.md, print the headlines, and re-derive the computed ones.

The table under "## Headline numbers" in docs/results.md is the single source of the headline
figures; the README carries a copy, and scripts/check_docs.py fails if the two differ. The table
under "## Raw counts" holds the counts the computed figures rest on. This script recomputes each
computed figure from those counts and confirms that results.md states it exactly as computed, so a
mistyped total, rate or floor cannot survive. Exit 1 on any mismatch. Standard library only.
"""
import os
import re
import sys

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(REPO_DIR, "docs", "results.md")
LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")


def table_under(text, heading):
    """Rows (lists of cells) of the first pipe table after the heading `## <heading>`.

    Returns [] when the heading or the table is missing, so callers can fail on absence."""
    lines = text.splitlines()
    try:
        start = next(i for i, l in enumerate(lines) if l.strip() == f"## {heading}")
    except StopIteration:
        return []
    rows, in_table = [], False
    for line in lines[start + 1:]:
        if line.startswith("## "):
            break
        if line.startswith("|"):
            in_table = True
            cells = [LINK.sub(r"\1", c).replace("**", "").strip() for c in line.strip().strip("|").split("|")]
            if not all(re.fullmatch(r":?-+:?", c) for c in cells):
                rows.append(cells)
        elif in_table:
            break
    return rows[1:]  # drop the header row


def headlines(path=RESULTS, heading="Headline numbers"):
    return table_under(open(path, encoding="utf-8").read(), heading)


def derive(path=RESULTS):
    """(statement, value as results.md must state it, stated?) for every computed figure."""
    text = open(path, encoding="utf-8").read()
    raw = {r[0]: int(r[1].replace(",", "")) for r in table_under(text, "Raw counts")}
    need = ["A-share cleansed orders", "A-share cleansed trades", "A-share cleansed quotes",
            "A-share typed layer, all three tables", "Crypto trades, stored",
            "Crypto L3 order-book events, stored", "Crypto incremental L2 book updates, stored"]
    missing = [k for k in need if k not in raw]
    if missing:
        return [(f"raw count missing: {k}", "", False) for k in missing]
    cleansed = sum(raw[k] for k in need[:3])
    crypto, typed = sum(raw[k] for k in need[4:]), raw["A-share typed layer, all three tables"]
    total, removed = cleansed + crypto, typed - cleansed
    reads = sum(v for k, v in raw.items() if k.startswith("Concurrency gate, reads"))
    figures = [
        ("A-share cleansed rows = orders + trades + quotes", f"{cleansed:,}"),
        ("the same, in billions", f"{cleansed / 1e9:.1f}B"),
        ("crypto stored rows, in billions", f"{crypto / 1e9:.1f}B"),
        ("crypto stored rows = trades + L3 events + L2 book updates", f"{crypto:,}"),
        ("A-share cleansed + crypto stored", f"{total:,}"),
        ("headline (holds while the stored sum is at least 700B)", "700B+" if total >= 700e9 else "below 700B"),
        ("crypto duplicate share above which 700B distinct fails",
         f"{(total - 700e9) / crypto * 100:.1f}%"),
        ("crypto duplicate share above which the 650B floor fails",
         f"{(total - 650e9) / crypto * 100:.1f}%"),
        ("rows cleansing removed = typed layer - cleansed layer", f"{removed:,}"),
        ("removal rate", f"{removed / typed * 100:.2f}%"),
        ("concurrency gate reads, all three reader kinds", f"{reads:,}"),
    ]
    return [(what, value, value in text) for what, value in figures]


def main():
    rows = headlines()
    if not rows:
        print("FAIL: no headline table under '## Headline numbers' in docs/results.md")
        return 1
    print("QTS research data platform: headline numbers (from docs/results.md)\n")
    for measure, result, label, source in rows:
        print(f"  {result:<24} {measure}")
        print(f"  {'':<24} label: {label}; source: {source}\n")
    print("Re-derived from the raw counts in docs/results.md:\n")
    bad = 0
    for what, value, stated in derive():
        bad += not stated
        print(f"  {'ok ' if stated else 'BAD'}  {value:<20} {what}"
              + ("" if stated else "  <- not stated this way in results.md"))
    print("\nLive = read from the running platform; Test = deliberate benchmark or gate.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
