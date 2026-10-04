# QTS research data platform: a showcase

A university quant society's research team needed tick-level market data it could trust and query
in seconds. As the team's sole developer, Oscar Choi built the platform that serves it: an
ingestion and cleansing pipeline plus a versioned reader library over **650B+ stored market-data
rows** (A-share cleansed plus crypto stored, table counts of 2026-10-03). Cleansing flags rows
instead of dropping them, after a time filter was found silently discarding **113,180**
closing-auction trades in one day; the only rows it removes are exact duplicates, **0.09%**.

```mermaid
flowchart LR
    src["Market data<br/>as delivered"] --> raw["raw<br/>byte-identical"]
    raw --> tab["typed Apache Parquet<br/>versioned"]
    tab --> cln["cleansed<br/>flagged, not dropped"]
    cln --> iface["one query interface<br/>Arrow out; DuckDB, Polars"]
```

```bash
bash scripts/demo.sh    # re-derives every computed figure in docs/results.md, then runs the stand-in
```

A write-up, not a code release: the platform's source is closed, so this repository holds none of
its code, no infrastructure detail and no data, and every number cites a dated source document by
title ([sources](docs/results.md#sources)). [demo/](demo/) is a separate stand-in, independent and
written only from this write-up, that runs the same ideas on SYNTHETIC data ([below](#run-the-stand-in)).
Implemented with AI coding agents under Oscar's design and review.

## The problem

The CUHK Quant Trading Society's researchers study A-share and crypto markets at tick level: every
trade, order and quote. Vendor deliveries arrive as compressed archives with their own quirks, and
the team had no full-time operator. Researchers needed three things the raw files could not give
them: data they could trust, queries that answer in seconds, and results they could reproduce
next month on exactly the same rows.

## Approach (methods and algorithms)

- **Three layers.** Raw files are kept byte-identical. A typed Apache Parquet layer holds the same rows,
  typed, with nothing corrected and nothing dropped. A cleansed layer adds labels and flags and
  corrects values while keeping the vendor's original; it removes only exact duplicates.
- **Versioned, pinned datasets.** Writers publish a whole new version or nothing; readers pin the
  version they started with, and can name one to reproduce a result later.
- **One interface.** The same call works wherever a researcher works. Asking for
  something that is not there raises an error rather than returning an empty table, and gap fills
  that read the future need an explicit opt-in. Results arrive as Apache Arrow data, and DuckDB SQL
  or Polars can read the same pinned versions directly.
- **Gates.** A property holds when a script that checks it exits 0, and every gate must be able to
  fail.

The call shapes, with invented names (the real interface is closed source):

```python
# ILLUSTRATIVE: invented function and argument names, not the real interface's signature.
trades = fetch("equities.trades", universe=["SYM_A"], from_="2024-03-01", to="2024-03-01")
bars   = fetch("equities.trades", from_="2024-03-01", to="2024-03-29", freq="1m")
closes = grid("equities.bars", column="close", from_="2024-01-02", to="2024-03-29", freq="1d")
```

More calls, and an illustrative output with SYNTHETIC values: [data-model.md](docs/data-model.md).

## Results

| Measure | Result | Label | Source |
|---|---|---|---|
| Stored market-data rows: A-share cleansed (565.9B) plus crypto stored (106.7B) | 650B+ | Live | table counts, 2026-10-03 |
| Closing-auction trades a time-window filter had silently dropped, one day | 113,180 | Test | data platform design, 2026-09-28 |
| A-share rows cleansing removed, all of them exact duplicates; every other rule labels, flags or corrects | 0.09% | Live | table counts, 2026-10-03 |
| Dataset commits on a small test dataset (420,000 rows) while 12 readers and 5 writers shared it | 23/23 commits, 0 lost | Test | concurrency gate results, 2026-09-23 |
| Whole-market day, warm: the query interface against hand-written DuckDB SQL | 1.49× slower | Test | data API benchmark, 2026-09-30 |

**Live**: read from the running platform. **Test**: a deliberate benchmark or gate. Speed is given
only as ratios; absolute timings are left out on purpose. Why 650B+ is a floor:
[results.md](docs/results.md#scale).

Three data-reading steps, timed by a scripted walkthrough of a researcher's work before and after a
round of fixes, ran 14×–99× faster; the same record's other everyday steps improved about 1.4–1.5×, and one about 5×
([results.md](docs/results.md#researcher-steps-before-and-after)).

The interface is **slower** than hand-written DuckDB SQL: 1.95× on one symbol-day and 1.49× on a
whole-market day, and about 3.5× on a bar request left out of the comparison because the two do
different work. That cost buys pinned versions, explicit errors, session labels and look-ahead
refusal, and it is published on purpose. Every figure, with its caveats:
[results.md](docs/results.md).

## How to run

There is no platform code here to run. `bash scripts/demo.sh` re-derives the computed figures and
runs the stand-in below; `bash scripts/check.sh` adds the document checks and the stand-in's tests.
To read in under five minutes: [results.md](docs/results.md) (every figure, its label, source and
caveats), [data-model.md](docs/data-model.md) (the layers, versioning, the interface and the data
decisions) and [reliability.md](docs/reliability.md) (gates, alerting and one incident).

### Run the stand-in

[demo/](demo/) holds **minilake**, an independent re-implementation of the ideas above, written
only from this write-up, on SYNTHETIC data. It is not the platform's code and shares none of it.
It uses the standard library only, so it runs anywhere in seconds: JSON column files stand in for a
columnar format, and the platform's own stack is deliberately not used.

```bash
cd demo && python3 -m minilake                    # every layer, then the gates; exit 0 only if all pass
cd demo && python3 -m unittest discover -s tests  # one test class per layer, plus the gates
```

It generates a small tick delivery with planted problems (exact duplicates, an evening print, a
price far off the previous trade, a crossed quote, trades stamped in UTC instead of exchange time,
and a missing day), then:

- **raw** keeps the files byte for byte and read-only under a checksum manifest; verification
  reports any altered byte;
- **typed** stores column-oriented day partitions under a schema; every publish is a new version
  folder with its manifest, made visible by one atomic rename (optimistic concurrency in the style
  of Delta Lake and Apache Iceberg), and readers pin a version. A replace that a concurrent commit
  has overtaken raises a conflict instead of discarding that commit;
- **cleansed** labels, flags or corrects and drops only exact duplicates. Each rule's hits are
  counted per day, every corrected cell goes into a correction log with the vendor's value, and a
  diff check proves cleansing changed only what the rules name;
- **query** is `fetch(universe, from_, to, freq=..., snapshot=..., gaps=...)`, with partition
  pruning and explicit errors. The read path hands over whole days, and an as-of guard withholds
  every row from `to` on; `gaps="carry_back"` looks only backwards, and `gaps="closest"` needs
  `permit_future=True`;
- **gates** check seven invariants. Each runs a control in the same run: a planted defect it must
  catch (an altered byte in a raw file and in a table file, unnamed changes, a non-atomic publish,
  a stale replace) or the synthetic ground truth it must match (planted counts, auction labels).
  Reader, writer and rewriter processes run under a deadline, so a crash or a hang fails the gate.
  The end of one run, abridged (counts of reads and rewrites vary between runs):

```text
  PASS  checksums        8 raw files verified, 0 problems; controls: altered raw byte caught: True; ...
  PASS  layer diff       8 table-days diffed, 0 unexplained changes; controls caught: unnamed value ...
  PASS  rule counts      found/planted: exact_duplicate 3/3, out_of_hours 1/1, off_band_price 1/1, ...
  PASS  auction labels   12 labelled closing_auction; ground truth 12 kept of 12 delivered; ...
  PASS  as-of guard      271 rows returned, last 2024-03-05T09:59:25.651 < 2024-03-05T10:00; ...
  PASS  pinned snapshot  v2 published over the pinned v1; fetch(snapshot=1) unchanged: True ...
  PASS  concurrency      4 readers, 2 writers, 1 rewriter: commits 40/40 acknowledged, lost 0; ...
  gates: 7/7 pass
```

## Architecture

### Design decisions and trade-offs

- **Flag, never drop.** A 09:15–15:00 filter had dropped 113,180 closing-auction trades on
  2026-09-24. Now only exact duplicates are deleted (0.09% of A-share rows); every other rule
  labels, flags or corrects a value, keeping the vendor's original, and is counted per day.
- **Three layers, not two.** Cleansing rules changed on the first day of review. The typed layer
  turns a rule change from days of re-decoding archives into hours, and shows exactly what each
  rule touched. Status, October 2026: with the rules settled, the A-share data is moving to one
  stored copy plus a small record of the cells cleansing changed and the duplicates it removed,
  enough to rebuild the typed layer exactly.
- **Compression measured, not assumed.** Asked whether storage could compress 10:1, the measured
  answer was no, on a different dataset that was already stored as compressed Parquet.
  (Converting raw A-share text to Parquet is about ten times smaller, 9.96× on two of the three
  tables of one day, but that is the file format, not a storage setting.) The level was then
  chosen by a rule written in advance:
  3.9% smaller, no slower to scan, 5.7× slower to write.
- **Profile before rewriting.** The slow query was not slow at reading data; caching the
  per-version file list made it 3.7–5.2× faster, where a rewrite in a compiled language would have
  sped up work that did not need doing.
- **Safety over peak speed.** The interface is 1.49× slower than hand-written DuckDB SQL on a
  whole-market day, and DuckDB over the same files stays available.

### How it was built

Oscar was the research team's sole developer: he set the requirements, designed the layers and
the gates, and reviewed every change. The code was written by AI coding agents under that design
and review; 815 of the 845 commits in the main repository carry an AI co-author trailer (count of
2026-10-03).

## Limits

- **The platform's numbers are not reproducible from here.** Its source and data are closed; the
  numbers rest on dated private records, described in [results.md](docs/results.md#sources).
- **The stand-in is not the platform.** [demo/](demo/) runs on SYNTHETIC data at toy scale; it
  shows the ideas and none of the platform's numbers.
- **No uptime or SLA figure.** No availability measurement exists that would support one.
- **The crypto count is a snapshot, not final**, and its exact-duplicate count was not recorded.
- **The query-fix ratios and the researcher-step ratios come from write-ups' tables** rather than
  raw per-run files, and the first query on a new nightly version, which rebuilds the cache, was not timed.
- **No researcher count or usage figure is reported**, because no dated record of one exists. The
  researcher-step ratios come from a scripted walkthrough of a researcher's steps, not from
  researchers.

## What I learned

1. **A setting found in a configuration file proves nothing until its effect is observed under
   load**: one such guarantee did nothing when it was finally measured. Source: decisions log,
   August 2026.

2. **The worst failures pass for health.** A check that passes against a stand-in for the thing it
   should be checking, a health check that answers OK without asking the service it describes, and
   an alerter that is quiet because it has stopped ([reliability.md](docs/reliability.md#failures-that-pass-for-health);
   source: handover document, 2026-09-07).

3. **A probe that runs out of time produces the same empty output as a broken system**, so how
   long the probe takes has to be known before its silence means anything. Source: decisions log,
   measurements of 2026-08-23.

4. **An unreliable checker does more harm than none, because its verdict gets trusted.** Hence
   checkers that carry self-tests and gates that refuse an empty run
   ([reliability.md](docs/reliability.md#a-claim-is-a-script-that-exits-0); source: decisions log,
   August 2026).

## Licence

Text and diagrams: CC BY 4.0. Code in scripts/ and demo/: MIT. Both in [LICENSE](LICENSE).
