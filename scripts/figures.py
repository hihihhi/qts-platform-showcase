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


def cell(text, heading, row, col):
    """Cell `col` of the row under `## heading` whose first cell starts with `row`; "" when absent."""
    return next((r[col] for r in table_under(text, heading) if r[0].startswith(row) and len(r) > col), "")


def paragraph(text, start):
    """The paragraph that begins with `start`; "" when absent."""
    return next((p for p in text.split("\n\n") if p.startswith(start)), "")


def says(where, value):
    """`value` appears in `where` as a whole figure, not inside a longer number such as 10.09%."""
    return re.search(r"(?<![\d,.])" + re.escape(value) + r"(?!\d|[,.]\d)", where) is not None


def derive(path=RESULTS):
    """(statement, value as results.md must state it, stated?) for every computed figure.

    Each figure must be stated at its own place: a figure that only appears somewhere else on the
    page, such as a rate mentioned in another row, does not count (review 2026-10-06)."""
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
    headline = lambda col: cell(text, "Headline numbers", "Stored market-data rows", col)
    removal = lambda col: cell(text, "Headline numbers", "A-share rows cleansing removed", col)
    scale = lambda row: cell(text, "Scale", row, 1)
    why = paragraph(text, "**Why 700B+")
    figures = [
        ("A-share cleansed rows = orders + trades + quotes", f"{cleansed:,}", [scale("A-share rows, cleansed")]),
        ("the same, in billions", f"{cleansed / 1e9:.1f}B", [headline(0)]),
        ("crypto stored rows, in billions", f"{crypto / 1e9:.1f}B", [headline(0)]),
        ("crypto stored rows = trades + L3 events + L2 book updates", f"{crypto:,}",
         [scale("Crypto rows, stored")]),
        ("A-share cleansed + crypto stored", f"{total:,}", [scale("Sum of the two")]),
        ("headline (holds while the stored sum is at least 700B)", "700B+" if total >= 700e9 else "below 700B",
         [headline(1), scale("Sum of the two")]),
        ("crypto duplicate share above which 700B distinct fails",
         f"{(total - 700e9) / crypto * 100:.1f}%", [why]),
        ("crypto duplicate share above which the 650B floor fails",
         f"{(total - 650e9) / crypto * 100:.1f}%", [why]),
        ("rows cleansing removed = typed layer - cleansed layer", f"{removed:,}",
         [scale("A-share rows removed by cleansing")]),
        ("removal rate", f"{removed / typed * 100:.2f}%",
         [removal(1), scale("A-share rows removed by cleansing")]),
        ("concurrency gate reads, all three reader kinds", f"{reads:,}",
         [cell(text, "Concurrency", "Reads", 1)]),
    ]
    return [(what, value, all(says(w, value) for w in where)) for what, value, where in figures]


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
