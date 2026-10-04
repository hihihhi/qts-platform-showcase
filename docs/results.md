# Results

Every number on this page comes from a dated source document, cited by **title and date**. The
documents themselves are private to the society; [Sources](#sources) lists what each one is. Each
figure carries one of two labels:

- **Live**: read from the running platform during normal or busy work.
- **Test**: a deliberate benchmark, gate or review measurement, on the running platform or on a
  stated sample of its data.

A † marks a figure taken from an evaluation write-up's prose or table, with no raw per-run result
file behind it. **Speed is given only as ratios** between two routes or two versions measured on
the same machine. Absolute timings are left out on purpose, because with a known data size they
would reveal how fast the machine is. There is no uptime or SLA figure, because no availability
measurement exists that would support one.

## Headline numbers

The README carries a copy of this table, and `scripts/check.sh` fails if the two differ in any
result, label or source.

| Measure | Result | Label | Source |
|---|---|---|---|
| Stored market-data rows: A-share cleansed (565.9B) plus crypto stored (138.1B) | 700B+ | Live | table counts, 2026-10-05 |
| Closing-auction trades a time-window filter had silently dropped, one day | 113,180 | Test | data platform design, 2026-09-28 |
| A-share rows cleansing removed, all of them exact duplicates; every other rule labels, flags or corrects | 0.09% | Live | table counts, 2026-10-05 |
| Dataset commits on a small test dataset (420,000 rows) while 12 readers and 5 writers shared it | 23/23 commits, 0 lost | Test | concurrency gate results, 2026-09-23 |
| Whole-market day, warm: the query interface against hand-written DuckDB SQL | 1.49× slower | Test | data API benchmark, 2026-09-30 |

## Raw counts

`scripts/demo.sh` reads this table and re-derives every computed figure on this page from it: the
A-share and crypto totals, the 700B+ sum, the duplicate shares that would break 700B and 650B, the
duplicate rate, and the read count. It exits 1 if any figure stated on this page disagrees with its
own arithmetic.

| Count | Value | Source |
|---|---:|---|
| A-share cleansed orders | 293,894,477,866 | table counts, 2026-10-05 |
| A-share cleansed trades | 228,609,088,757 | table counts, 2026-10-05 |
| A-share cleansed quotes | 43,446,124,248 | table counts, 2026-10-05 |
| A-share typed layer, all three tables | 566,464,087,478 | table counts, 2026-10-05 |
| Crypto trades, stored | 137,221,906,250 | table counts, 2026-10-05 |
| Crypto L3 order-book events, stored | 698,762,007 | table counts, 2026-10-05 |
| Crypto incremental L2 book updates, stored | 138,932,302 | table counts, 2026-10-05 |
| Concurrency gate, reads by the first reader kind | 282 | concurrency gate results, 2026-09-23 |
| Concurrency gate, reads by the second reader kind | 410 | concurrency gate results, 2026-09-23 |
| Concurrency gate, reads by the third reader kind | 419 | concurrency gate results, 2026-09-23 |

## Scale

| Measure | Result | Label | Source |
|---|---|---|---|
| A-share rows, cleansed layer (orders, trades and quotes) | 565,949,690,871 | Live | table counts, 2026-10-05 |
| Crypto rows, stored: trades from 2019-03-30 to 2026-09-29, L3 order-book events from 2026-06-01 and incremental L2 book updates from 2026-08-01, both to 2026-10-01 | 138,059,600,559 | Live | table counts, 2026-10-05 |
| Sum of the two, stored rows | 704,009,291,430, stated as **700B+** | Live | table counts, 2026-10-05 |
| A-share rows removed by cleansing (typed layer minus cleansed layer, both covering the same days), all exact duplicates | 514,396,607 of 566,464,087,478, which is 0.09% | Live | table counts, 2026-10-05 (counts); table counts, 2026-10-03 (day ranges); data platform design, 2026-09-28 (only exact duplicates are removed) |
| A-share history covered | 2,361 trading days of trades from 2017-01-03 to 2026-09-28 in the wiki build of 2026-10-01; the table counts of 2026-10-03 run to 2026-09-30 | Live | researcher wiki, pipeline and cleansing pages, built 2026-10-01 |

**Why 700B+ counts stored rows, not distinct ones.** The crypto figure counts stored rows. Its
cleansed view is meant to leave out exact duplicates but does not exclude them yet, so today it
holds the same count; no count of crypto duplicates has been recorded, and a re-cleanse is in
progress. How many of the stored rows are distinct is therefore unmeasured. As a count of distinct
rows, 700B holds only if fewer than 2.9% of the crypto rows are exact duplicates (704.01B minus
700B leaves 4.01B of the 138.06B). The conservative floor is 650B, which holds unless more than
39.1% of them are (704.01B minus 650B leaves 54.01B). For comparison, A-share cleansing found 0.09%
exact duplicates. No row is counted twice: the A-share typed layer is a separate copy and is not
added. The crypto counts are a snapshot, not final.

**Gaps in the A-share history.** One trading day is missing because the supplier's archive for it
was damaged, and three days of trades are held back in the raw layer because of a column anomaly.
Source: A-share data-issues record, 2026-09-30.

**Why the crypto count jumped.** A dated record of 2026-09-30 held 16,015,162,350 crypto rows, and
the table counts of 2026-10-03 hold 106,705,605,608 (137,221,906,250 crypto trades by the table
counts of 2026-10-05). The converter had been crash-looping on one
oversized batch, 743 times, committing nothing behind it. The count did not grow steadily: the two
dated counts bracket the fix, after which the converter committed the files that had queued behind
the failing batch ([the story](reliability.md#a-second-shorter-story-the-converter-that-crash-looped)).
Sources: crypto dataset baseline, 2026-09-30; converter fix commit record, 2026-10-03; table
counts, 2026-10-03 and 2026-10-05.

## Concurrency

12 readers, reading through DuckDB, Apache Arrow and the query interface, read one small test
dataset while 4 writers appended to it and a fifth process rewrote one of its partitions. It is a
correctness test of versioning under contention, not a load test.

| Measure | Result | Label | Source |
|---|---|---|---|
| Dataset commits | 23/23, 0 lost, 0 writer errors | Test | concurrency gate results, 2026-09-23 |
| Reads | 1,111, with 0 errors and 0 mismatches against the version each read had pinned | Test | concurrency gate results, 2026-09-23 |
| Final dataset | 420,000 rows exactly: every writer's batch once | Test | concurrency gate results, 2026-09-23 |

## The query fix

A one-symbol, one-day query was slower than it should have been. The obvious fix, reading only the
partitions the query names, barely moved it. A profile showed that most of the time went into
rebuilding the list of a dataset version's files on every query, not into reading data. Building
that list once per version and keeping it fixed the query. Rewriting the service in a compiled
language, which the brief allowed, would only have sped up work that did not need doing.

| Measure, warm cache | Ratio, before to after | Label | Source |
|---|---|---|---|
| One query | 3.7–5.2× faster (worst and best pairing of the before and after ranges) | Test† | database evaluation, 2026-09-23 |
| Partition pruning alone, same query | 0.97–1.24×: no reliable gain | Test† | database evaluation, 2026-09-23 |
| Eight of the same query at once, wall time | 6.9× faster | Test† | database evaluation, 2026-09-23 |

"Warm" means the per-version file list is already built. A new version arrives every night, so the
first query on new data rebuilds it; the record does not time that first query.

## Researcher steps, before and after

A researcher's everyday steps were timed before and after a round of fixes, by a scripted
walkthrough of those steps rather than by researchers. Ratios only, both sides on the same machine.
The three rows below are the data-reading steps. The record's other everyday steps, which do not
read data, improved only about 1.4–1.5×, and one about 5×.

| Step, before to after | Ratio | Label | Source |
|---|---|---|---|
| One symbol, one day, read | about 25× faster | Test† | whole-system evaluation, 2026-09-23 |
| A week of trades, queried in SQL | 14× faster | Test† | whole-system evaluation, 2026-09-23 |
| A day of quotes, read into a dataframe library | 99× faster | Test† | whole-system evaluation, 2026-09-23 |

## Where the interface is slower

The query interface was benchmarked against hand-written DuckDB SQL over the same Parquet files, on
the same request shapes. The ratio compares the medians (p50) of the runs.

| Request, warm | Runs | Interface against hand-written DuckDB | Label | Source |
|---|---:|---|---|---|
| One symbol, one day, every row | 5 | 1.95× slower | Test | data API benchmark, 2026-09-30 |
| Every symbol, one day, every row | 3 | 1.49× slower | Test | data API benchmark, 2026-09-30 |

**Hand-written DuckDB wins on both.** The interface spends that time on what it adds over raw
files: it pins a dataset version, raises an explicit error instead of returning a silent empty
result, labels trading sessions by exchange and date, and refuses gap fills that read the future
unless the caller opts in. The trade was made on purpose: a researcher who needs the last factor
of two can still write DuckDB SQL against the same files.

**Bar requests are left out of the comparison, including the interface's worst ratio.** For
1-minute bars the interface reads stored bars, while the hand-written SQL computed bars from trades
with no session calendar: different work, with different results on two of the three bar shapes.
On the third, one symbol for one day, both returned the same number of rows and the interface was
about 3.5× slower. It is excluded because the work differs, not because it is unflattering.

## Data quality: decisions that measurement changed

| Measure | Result | Label | Source |
|---|---|---|---|
| Trades dropped by a 09:15–15:00 filter on 2026-09-24 | 113,180 closing-auction trades | Test | data platform design, 2026-09-28 |
| The same filter on 2023-06-01 | 238,632 trades | Test | data platform design, 2026-09-28 |
| Raw A-share text files to Parquet, two of the three tables of one A-share day, in a format experiment at a moderate compression level | 9.96× smaller | Test (one day) | cleansed-format evidence, 2026-09-22 |
| Typed Parquet layer against the supplier's own compressed delivery, one A-share day | 0.86× the size | Test (one day) | code-and-library evaluation, 2026-09-23 |
| Highest compression level against a moderate level, one real A-share day | 3.9% smaller; no slower to scan; writing took 5.7× as long | Test | compression-level measurement, 2026-09-23 |

A 10:1 ratio had been asked for and measured as not achievable from storage, on a different dataset
already stored as compressed Parquet (decisions log, August 2026). The 9.96× above is the file format, not a storage setting.
The reasoning behind each decision is in [data-model.md](data-model.md#decisions-the-data-forced).

## How it was built

| Measure | Result | Label | Source |
|---|---|---|---|
| Commits in the main platform repository | 845, of which 815 carry an AI co-author trailer | Live, read-only count | count taken for this write-up, 2026-10-03 |
| Human authors in that repository's history, through 2026-10-03 | 1 (Oscar) | Live, read-only count | count taken for this write-up, 2026-10-05 |

Commit counts measure activity, not outcomes; they are here only to show how the work was done.

## Sources

The source documents are private to the society. None is linked, and none is quoted beyond the
figures above.

| Cited as | What it is |
|---|---|
| table counts, 2026-10-03 | raw output of the platform's table listing: every table, its row count and its day range |
| table counts, 2026-10-05 | a later read-only run of the same table listing, taken through the platform's own interface (2026-10-04 20:20 UTC): every table, its row count and its day range |
| concurrency gate results, 2026-09-23 | raw output of the readers-and-writers gate |
| database evaluation, 2026-09-23 | an evaluation and profile of the query path, written up in prose and tables |
| code-and-library evaluation, 2026-09-23 | an evaluation of the platform's code and libraries, including the stored size of one A-share day's three tables against the supplier's archive |
| data API benchmark, 2026-09-30 | raw output: the query interface, hand-written DuckDB SQL and the interface's other delivery paths, on five request shapes, 3 or 5 runs each |
| whole-system evaluation, 2026-09-23 | a researcher's everyday steps timed before and after fixes by a scripted walkthrough, including DuckDB and Polars reading through the versioned dataset |
| data platform design, 2026-09-28 | the three-layer design, and a review of an earlier cleansing script against the data |
| researcher wiki, pages built 2026-10-01 | the generated documentation researchers read: pipeline and cleansing pages |
| A-share data-issues record, 2026-09-30 | days the supplier delivered damaged or anomalous, found while converting every raw day |
| crypto dataset baseline, 2026-09-30 | raw row counts and checksums of the crypto trades dataset |
| converter fix commit record, 2026-10-03 | the change that ended the crypto converter's crash loop, with its gate |
| cleansed-format evidence, 2026-09-22 | one A-share day converted from the raw text files to Parquet, with sizes |
| compression-level measurement, 2026-09-23 | four compression levels written for one real A-share day |
| decisions log, August 2026 | the platform's dated record of choices and the measurements behind them, including the 10:1 request and its answer, and the measurements of 2026-08-23 cited in the README's lessons |
| crypto cleansing rules, 2026-10-01 | the crypto trades' cleansing rules, including why that dataset keeps one copy |
| single-copy plan, 2026-10-03 | the plan, and its progress, for moving the A-share data to one stored copy |
| alerter design notes and change history, 2026-09-05 to 2026-10-03 | how failures reach a person: the 2026-09-05 measurement of the unread failure log, the fixes rejected and the one made |
| handover document, 2026-09-07 | how to run the platform, and its failure modes that look like success |
| count taken for this write-up, 2026-10-03 | a read-only count over the closed repository's history |
| count taken for this write-up, 2026-10-05 | a read-only count of distinct human authors in the same history, up to 2026-10-03 |
