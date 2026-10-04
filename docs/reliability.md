# Reliability practice

How the platform decides that something works, and how it finds out when something stops working.
This page stays at the level of practice: it names no machines, services or infrastructure. There
is no uptime or SLA figure, and none is claimed.

## A claim is a script that exits 0

Whether something works is decided by a **gate**: a script that checks the running platform and
exits 0 only if one stated property holds. "The cleansed layer covers every day of the typed layer"
and "the alerter has run recently and can still report a failure" are each a gate. A change is done
when its gate exits 0, not when it looks done.

A gate is only worth having if it can fail, so the gates themselves are held to rules:

- **An empty run is a failure.** A test suite that collected nothing exits 0, and "0 tests passed"
  is exactly the vacuous result a gate exists to stop.
- **A test that reports a failure but exits 0 is rejected.** This rule came from a test that had
  printed two failures on every run while reporting PASS.
- **Checkers carry self-tests.** Each is fed a known defect and must turn red. More than once, a first-run gate
  failure turned out to be the instrument, not the thing it measured.
- **Every negative check has a positive control in the same run.** A probe that sees "nothing wrong"
  proves nothing if it never looked. The converter gate below is an example: the unfixed operation
  must still fail on the oversized input, and the fixed one must pass.

## Failures that pass for health

Some faults leave every check green. The ones met here are now checked directly:

- **A quiet alerter and a dead alerter look the same**, unless the alerter proves it is alive.
- **A probe that runs out of time prints nothing**, which is also what a healthy probe prints, so a
  timeout is reported as a finding in its own right.
- **A check can pass against a stand-in for the thing it should be checking.** A check that only
  asks "is something there?" passes; the checks ask whether it is the real thing.
- **A health check can answer OK without asking the service it describes.** The checks ask the
  service itself.

## Incident: thirteen days of failures that reached nobody

Told from the alerter's design notes and change history (2026-09-05 to 2026-10-03) and the
platform's handover document (2026-09-07).

| When | What happened |
|---|---|
| for 13 days to 2026-09-05 | A scheduled health check fails every ten minutes. Each failure is written to a log on the machine it watches. Nothing is delivered to anyone. |
| before 2026-09-05 | A researcher reports an outage by hand. The checks had already detected it hours earlier and written it, in plain language, to a log nobody read. |
| 2026-09-05 | Measured: 29,754 unread lines in the failure log. **Finding:** detection worked; delivery did not exist. |
| 2026-09-05 | Rejected fix: forward the log as it is. That would have sent one message per failure line, on the order of the 29,754 already unread (an estimate; it was never sent), been muted within a minute, and left everyone as blind as before while believing otherwise. |
| 2026-09-05 to 2026-09-07 | The alerter is built: one message when a fault starts and one when it clears, a remembered state so that a new fault stands out, and a heartbeat on every run so that silence can no longer mean both "healthy" and "dead". Its self-test catches an alert-fatigue bug on its first run: a fallback that re-announced every known fault on every quiet run. |
| 2026-09-07 | An audit finds that the alerter had no time limit anywhere. The very fault it existed to report could hang it, and every later run was then skipped. Fix: every read is bounded, and a timeout is itself reported. The delivery steps get the same treatment. |
| 2026-09-30 | Alerts stop depending on the health of the machine they report on, and a second, independent watcher raises the alarm if the regular check-in stops. |
| 2026-10-03 | An alert audit turns each recent silent failure into a probe and proves delivery end to end. |

**The gates it left.** One gate fails unless the alerter has run within its interval and can still
report a failure. Another fails if the latest check-in is more than ten minutes old. Clearing an
alert requires measuring its condition again; a cleared alert is archived, not erased.

## A second, shorter story: the converter that crash-looped

The crypto converter turns each raw file into the platform's checked copy. One batch held a text
column larger than the converter's in-memory format could address in one piece. The converter
crash-looped on that batch 743 times and committed nothing behind it. The fix processes that case
in smaller pieces and converts the result back to the stored types; its gate keeps the control
described above.

The dated crypto count rose from 16,015,162,350 rows (2026-09-30) to 106,705,605,608 (2026-10-03).
The count did not grow steadily: the two dated counts bracket the fix, after which the converter
committed the files that had queued behind the failing batch. Sources: converter fix commit record, 2026-10-03; crypto dataset baseline, 2026-09-30;
table counts, 2026-10-03.

## Concurrency, tested rather than argued

12 readers, reading through DuckDB, Apache Arrow and the query interface, ran against one small test dataset while 4 writers appended and
a fifth process rewrote a partition. The result: 23/23 commits with none lost and no writer errors,
1,111 reads with no errors and no mismatch against each read's pinned version, and a final dataset
of exactly 420,000 rows, every writer's batch once. Source: concurrency gate results, 2026-09-23.
