#!/usr/bin/env python3
"""The repository's test. It holds documents only, so it checks what can break in them.

    check_docs.py              run every check on this repository; exit 0 only if all pass
    check_docs.py --self-test  plant one defect per check in a scratch copy; each must go red,
                               and the untouched copy (the control) must stay green

Checks, each with the failure it exists to catch:
  links     a relative link or #anchor in README.md or docs/*.md that points nowhere
  fences    an unclosed code fence (it swallows the rest of the page on GitHub), or a mermaid
            block that is empty or does not start with a diagram type (GitHub shows an error box)
  headlines the README's headline table differing from docs/results.md in any result, label or
            source, or either table missing
  arithmetic a computed figure in docs/results.md (a total, the 700B+ sum and its duplicate shares, the duplicate rate,
            the read count) that its own raw counts do not produce (scripts/figures.py)
  numbers   a figure in the README's prose that docs/results.md does not state
  forbidden a hardware, access or vendor term anywhere in the repository, this file included
            (only its pattern lists are skipped). This check blocks; it never just informs.
            Further patterns, one regex per line, are read from the file named by the environment
            variable FORBIDDEN_TERMS_FILE when it is set; that file is never committed.
Standard library only.
"""
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from figures import derive, headlines  # noqa: E402

SELF = os.path.relpath(os.path.abspath(__file__), os.path.dirname(HERE))
LINK = re.compile(r"\]\(([^)\s]+)\)")
FENCE = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")
HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
MERMAID_TYPES = ("flowchart", "graph", "sequenceDiagram", "stateDiagram", "timeline", "xychart-beta")

# --- pattern lists: the only lines of this file the forbidden-terms scan skips ---
MIT_TEXT = """Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""

# Generic words only; anything more specific would describe a real setup if listed here. Units are
# banned outright, because a size or a rate next to a duration encodes the hardware.
GENERIC = [
    r"\bGPUs?\b", r"\bRAM\b", r"\bthreads?\b", r"\bcores?\b", r"\bNAS\b", r"\bSSH", r"\bVPN\b",
    r"\bsudo\b", r"\broot\b", r"passwords?",
    r"\d\s?(?:KB|MB|GB|TB|PB|KiB|MiB|GiB|TiB)\b", r"\b(?:KB|MB|GB|TB)/s\b", r"\brows/s\b", r"\d\s?[GM]bps\b",
]
# Vendor and brand names are caught by shape, so that the names themselves never ship in this
# file: any domain name, and any all-capitals word that is not on the short list of terms this
# write-up uses. github.com is allowed for the link to the stand-in's repository.
DOMAIN = r"\b[a-z0-9-]+\.(?:com|net|org|io|cn|hk|ai|dev|xyz|co)\b"
DOMAIN_OK = {"creativecommons.org", "github.com"}
ACRONYM = re.compile(r"(?<![\w-])[A-Z][A-Z0-9]{2,}(?![\w-])")
ACRONYM_OK = {
    "API", "CUHK", "QTS", "SQL", "SLA", "README", "LICENSE", "PASS", "FAIL", "ILLUSTRATIVE",
    "SYNTHETIC", "MIT", "OUTPUT", "CHECK", "PINNED", "NOT", "FORBIDDEN", "TERMS", "FILE", "UTC", "DIAGRAMS",
}
# --- end of pattern lists ---
# Whole lines, compared exactly: a marker with text after it is not a marker, so nothing can hide on one.
BLOCK_START = "# --- pattern lists: the only lines of this file the forbidden-terms scan skips ---"
BLOCK_END = "# --- end of pattern lists ---"
# Extra patterns from a file outside the repository; unset in CI, where the line printed says so.
PRIVATE = os.environ.get("FORBIDDEN_TERMS_FILE", "")


def documents(tree):
    docs = ["README.md"] + sorted(os.path.join("docs", f) for f in os.listdir(os.path.join(tree, "docs"))
                                  if f.endswith(".md"))
    return [d for d in docs if os.path.isfile(os.path.join(tree, d))]


def slug(text):
    """GitHub's heading anchor: lower-case, drop punctuation, spaces to hyphens."""
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text).lower().replace("`", "")
    return re.sub(r"[^\w\- ]", "", text).replace(" ", "-")


def parse(path):
    """(prose lines outside fences, heading anchors, fence errors) for one markdown file."""
    prose, anchors, errors, seen, fence = [], set(), [], {}, None
    for n, line in enumerate(open(path, encoding="utf-8").read().splitlines(), 1):
        m = FENCE.match(line)
        if fence is None:
            if m:
                fence = (m.group(1), m.group(2).strip(), n, [])
                continue
            prose.append((n, line))
            h = HEADING.match(line)
            if h:
                s = slug(h.group(2))
                k = seen.get(s, 0)
                seen[s] = k + 1
                anchors.add(s if k == 0 else f"{s}-{k}")
            continue
        marker, info, start, body = fence
        if m and m.group(2).strip():
            errors.append(f"{path}:{start}: {info or 'code'} fence still open when another opens at line {n}")
        if m and m.group(1)[0] == marker[0] and len(m.group(1)) >= len(marker) and not m.group(2).strip():
            if info == "mermaid":
                first = next((b.strip() for b in body if b.strip()), "")
                if not first.startswith(MERMAID_TYPES):
                    errors.append(f"{path}:{start}: mermaid block empty or without a diagram type: {first[:40]!r}")
            fence = None
        else:
            body.append(line)
    if fence is not None:
        errors.append(f"{path}:{fence[2]}: {fence[1] or 'code'} fence opened here is never closed")
    return prose, anchors, errors


def check_links_and_fences(tree):
    parsed = {d: parse(os.path.join(tree, d)) for d in documents(tree)}
    errors, mermaid = [], 0
    for doc, (prose, anchors, ferrs) in parsed.items():
        errors += ferrs
        mermaid += open(os.path.join(tree, doc), encoding="utf-8").read().count("```mermaid")
        for n, line in prose:
            for target in LINK.findall(line):
                if re.match(r"[a-z][a-z0-9+.-]*:", target):
                    continue  # external URL: not checked offline
                file_part, _, anchor = target.partition("#")
                dest = os.path.normpath(os.path.join(os.path.dirname(doc), file_part)) if file_part else doc
                if not os.path.exists(os.path.join(tree, dest)):
                    errors.append(f"{doc}:{n}: link to missing file {target}")
                elif anchor and (dest not in parsed or anchor not in parsed[dest][1]):
                    errors.append(f"{doc}:{n}: no heading for anchor {target}")
    if mermaid == 0:
        errors.append("README.md: the data-flow diagram is missing (no mermaid block in any document)")
    return errors


def check_headlines(tree):
    ours = headlines(os.path.join(tree, "docs", "results.md"))
    theirs = headlines(os.path.join(tree, "README.md"), "Results")
    if not ours or not theirs:
        return ["headline table missing from docs/results.md or from the README's Results section"]
    if [r[1:] for r in ours] != [r[1:] for r in theirs]:
        return ["README headline table differs from docs/results.md (result, label or source)"]
    return []


NUMBER = re.compile(r"\d[\d,.:/–-]*\d(?:B\+?|%|×)?|\d(?:B\+?|%|×)")


def check_numbers(tree):
    """Every figure in the README's prose must be stated in docs/results.md."""
    results = open(os.path.join(tree, "docs", "results.md"), encoding="utf-8").read()
    prose, _, _ = parse(os.path.join(tree, "README.md"))
    errors = []
    for n, line in prose:
        line = re.sub(r"\]\([^)]*\)", "]", line)  # link targets are paths, not figures
        for tok in NUMBER.findall(line):
            tok = tok.rstrip(".,")
            if re.fullmatch(r"\d{1,2}", tok) or tok == "4.0":  # list numbering, small counts, the licence
                continue
            if tok not in results:
                errors.append(f"README.md:{n}: figure {tok!r} is not stated in docs/results.md")
    return errors


def check_arithmetic(tree):
    results = os.path.join(tree, "docs", "results.md")
    return [f"docs/results.md: {what}: {value!r} is not stated" for what, value, ok in derive(results) if not ok]


def private_patterns(path):
    """The patterns in a private terms file: one per line, blank lines and # comments skipped."""
    lines = (l.strip() for l in open(path, encoding="utf-8"))
    return [l for l in lines if l and not l.startswith("#")]


def check_forbidden(tree, private=PRIVATE):
    patterns = [(p, re.compile(p, re.I)) for p in GENERIC + [DOMAIN]]
    if private:
        # A terms file that is missing or holds no pattern would scan for nothing and read as clean.
        found = private_patterns(private) if os.path.isfile(private) else []
        if not found:
            return ["FORBIDDEN_TERMS_FILE is missing or holds no patterns: the private scan would check nothing"]
        patterns += [("<private pattern>", re.compile(p, re.I)) for p in found]
    # The standard MIT text uses words the scan forbids elsewhere. Only lines that are exactly
    # the canonical MIT text are exempt, and only in LICENSE, so the file cannot hide anything else.
    mit_lines = {l.strip() for l in MIT_TEXT.splitlines() if l.strip()}
    errors = []
    marks = [BLOCK_START, BLOCK_END]
    for d, dirs, files in os.walk(tree):
        dirs[:] = [x for x in dirs if x not in (".git", "__pycache__", ".ruff_cache")]  # never committed (.gitignore)
        for f in files:
            rel = os.path.relpath(os.path.join(d, f), tree)
            try:
                text = open(os.path.join(tree, rel), encoding="utf-8").read()
            except UnicodeDecodeError:
                errors.append(f"{rel}: not UTF-8 text; a binary file cannot be scanned, so it may not ship")
                continue
            in_block, lines = False, text.splitlines()
            if rel == SELF:
                # Without exactly one start line and one end line, in that order, a deleted end marker
                # would switch the scan off for the rest of the file: refuse, and skip nothing.
                at = [[i for i, l in enumerate(lines) if l.rstrip() == m] for m in marks]
                if not (len(at[0]) == len(at[1]) == 1 and at[0][0] < at[1][0]):
                    errors.append(f"{rel}: the pattern-list start and end markers must each appear once as a "
                                  "whole line, start first; nothing in this file is skipped until they do")
                    marks_ok = False
                else:
                    marks_ok = True
            for n, line in enumerate(lines, 1):
                if rel == SELF and marks_ok and line.rstrip() in marks:
                    in_block = line.rstrip() == BLOCK_START
                    continue
                if in_block:
                    continue  # the pattern lists themselves, and nothing else in this file
                if rel == "LICENSE" and line.strip() in mit_lines:
                    continue
                for label, rx in patterns:
                    # every match, so an allowed domain earlier on a line cannot hide a later one
                    for m in rx.finditer(line):
                        if label == DOMAIN and m.group(0).lower() in DOMAIN_OK:
                            continue
                        shown = m.group(0) if label != "<private pattern>" else "<redacted>"
                        errors.append(f"{rel}:{n}: forbidden term {shown!r} ({label})")
                # Code uses capitals for constants, so the shape rule reads prose and config only.
                for m in ([] if rel.endswith(".py") else ACRONYM.finditer(line)):
                    if m.group(0) not in ACRONYM_OK:
                        errors.append(f"{rel}:{n}: unlisted all-capitals word {m.group(0)!r}: a possible vendor or "
                                      "hardware name; add it to ACRONYM_OK only if it is neither")
    return errors


CHECKS = [("links and fences", check_links_and_fences), ("headlines", check_headlines),
          ("arithmetic", check_arithmetic), ("numbers", check_numbers), ("forbidden terms", check_forbidden)]


def run(tree):
    if PRIVATE and os.path.isfile(PRIVATE):
        n = len(private_patterns(PRIVATE))
        print(f"INFO  forbidden terms: generic list and shape rules, plus {n} patterns from FORBIDDEN_TERMS_FILE")
    elif PRIVATE:
        print("FAIL  FORBIDDEN_TERMS_FILE is set but is not a file")  # a typo must not read as a clean scan
        return 1
    else:
        print("INFO  forbidden terms: generic list and shape rules only (FORBIDDEN_TERMS_FILE not set)")
    failed = 0
    for name, fn in CHECKS:
        errors = fn(tree)
        for e in errors[:30]:
            print(f"  FAIL {e}")
        print(f"{'FAIL' if errors else 'PASS'}  {name}")
        failed += bool(errors)
    return failed


def self_test():
    """Each mutant plants one defect in a scratch copy and must turn exactly the named checks red."""
    def edit(path, old, new):
        def apply(tree):
            p = os.path.join(tree, path)
            text = open(p, encoding="utf-8").read()
            assert old in text, f"self-test anchor {old!r} not in {path}"
            open(p, "w", encoding="utf-8").write(text.replace(old, new, 1))
        return apply

    def append(path, text):
        return lambda tree: open(os.path.join(tree, path), "a", encoding="utf-8").write(text)

    cases = [
        ("control", None, None),
        ("broken link", "links and fences", edit("README.md", "(docs/data-model.md)", "(docs/missing.md)")),
        ("broken anchor", "links and fences", edit("README.md", "results.md#scale", "results.md#no-such-heading")),
        ("unclosed fence", "links and fences", append("docs/reliability.md", "\n```text\nnever closed\n")),
        ("empty mermaid", "links and fences", append("docs/reliability.md", "\n```mermaid\n```\n")),
        # a drifted headline is also a figure results.md does not state, so two checks go red
        ("headline drift", ["headlines", "numbers"], edit("README.md", "| 700B+ |", "| 750B+ |")),
        ("label drift", "headlines", edit("README.md", "| 1.49× slower | Test |", "| 1.49× slower | Live |")),
        ("README-only figure", "numbers", edit("README.md", "discarding **113,180**", "discarding **113,181**")),
        ("miscomputed total", "arithmetic", edit("docs/results.md", "| 43,446,124,248 |", "| 43,446,124,249 |")),
        # Every planted term is made up, so the fixtures describe nothing real. Each is assembled
        # at run time, because this file is scanned too and must not match its own fixtures.
        ("generic word", "forbidden terms", append("docs/data-model.md", "\nThe job asked for 4096 thr" + "eads.\n")),
        ("size unit", "forbidden terms", append("docs/results.md", "\nThe layer takes 999 " + "PB.\n")),
        ("vendor-shaped name", "forbidden terms", append("docs/results.md", "\nData came from ACMEDATA.\n")),
        ("domain name", "forbidden terms", append("docs/results.md", "\nSee acme-data" + ".com for files.\n")),
        ("allowed domain hiding another", "forbidden terms",
         append("docs/results.md", "\nSee github" + ".com and acme-data" + ".com.\n")),
        ("private-list hardware word", "forbidden terms", append("docs/data-model.md", "\nIt ran on a zzhw" + "term card.\n")),
        ("private-list access word", "forbidden terms", append("README.md", "\nResearchers connect through zzaccess" + "term.\n")),
        # Review 2026-10-06. A headline moved in both documents still has to match its own arithmetic:
        # 0.09% is stated elsewhere on the page, which must not be enough.
        ("headline figure moved in both documents", "arithmetic",
         lambda tree: [edit(f, "| 0.09% | Live |", "| 0.10% | Live |")(tree) for f in ("README.md", "docs/results.md")]),
        ("empty private list", "forbidden terms", None, "empty"),
        ("missing private list", "forbidden terms", None, "missing"),
        # the pattern-list skip must not be switchable by a deleted or decorated marker line
        ("end marker deleted", "forbidden terms",
         lambda tree: [edit(SELF, BLOCK_END, "")(tree), append(SELF, "\nThe job asked for 4096 thr" + "eads.\n")(tree)]),
        ("text after a marker", "forbidden terms",
         edit(SELF, BLOCK_END, BLOCK_END + " 4096 thr" + "eads")),
        ("ignored cache folder", None,
         lambda tree: (os.makedirs(os.path.join(tree, ".ruff_cache"), exist_ok=True),
                       open(os.path.join(tree, ".ruff_cache", "x"), "wb").write(b"\xff\xfe"))),
    ]
    base = tempfile.mkdtemp(prefix="showcase-selftest-")
    repo = os.path.dirname(HERE)
    # A scratch private list proves the private-file path works whether or not the real one exists.
    private = os.path.join(base, "private-terms.txt")
    open(private, "w", encoding="utf-8").write("# scratch\n\\bzzhw" + "term\\b\n\\bzzaccess" + "term\\b\n")
    privates = {"empty": os.path.join(base, "empty-terms.txt"), "missing": os.path.join(base, "absent.txt")}
    open(privates["empty"], "w", encoding="utf-8").write("# only comments\n   # an indented one\n\n")
    bad = 0
    try:
        for label, target, mutate, *use in cases:
            tree = os.path.join(base, label.replace(" ", "-"))
            shutil.copytree(repo, tree, ignore=shutil.ignore_patterns(".git", "__pycache__", ".ruff_cache"))
            if mutate:
                mutate(tree)
            red = [name for name, fn in CHECKS
                   if (fn(tree, privates[use[0]] if use else private) if fn is check_forbidden else fn(tree))]
            want = target if isinstance(target, list) else [target] if target else []
            ok = red == want
            bad += not ok
            print(f"  {'ok ' if ok else 'BAD'} {label}: red checks {red or 'none'}"
                  + ("" if ok else f", expected {want or 'none'}"))
    finally:
        shutil.rmtree(base, ignore_errors=True)
    print(f"{'PASS' if not bad else 'FAIL'}  self-test ({len(cases)} cases, {bad} wrong)")
    return bad


def main():
    if sys.argv[1:] == ["--self-test"]:
        return 1 if self_test() else 0
    if sys.argv[1:]:
        print(__doc__.strip())
        return 2
    return 1 if run(os.path.dirname(HERE)) else 0


if __name__ == "__main__":
    sys.exit(main())
