# Diagrams

Every diagram in this write-up, numbered. Each node is a layer, a step or a check the write-up
describes; the platform's code is closed, so each diagram names the page that describes it instead
of a path. If a diagram and the code disagree, the code wins.

1. [System overview](#1-system-overview)
2. [Versioned publish under concurrent readers and writers](#2-versioned-publish-under-concurrent-readers-and-writers)
3. [Three layers: what changes each one](#3-three-layers-what-changes-each-one)
4. [Look-ahead refusal](#4-look-ahead-refusal)
5. [The alerting incident: detection worked, delivery did not](#5-the-alerting-incident-detection-worked-delivery-did-not)

## 1. System overview

The layers a delivery passes through, the versioned dataset they are published to, and the readers that see it; the accented path is the one this write-up is about.

```mermaid
flowchart TB
    src["Market data<br/>as delivered"]
    subgraph pipe["Ingestion and cleansing pipeline"]
        direction LR
        raw[("raw<br/>byte-identical")]
        tab[("typed Apache Parquet<br/>the same rows, typed")]
        cln[("cleansed<br/>labels and flags")]
    end
    subgraph ds["Versioned dataset"]
        ver[("every table a<br/>sequence of versions")]
    end
    subgraph rd["Readers"]
        direction LR
        api["one query interface"]
        arrow["Apache Arrow data"]
        duck["DuckDB SQL"]
        pol["Polars"]
    end
    src -->|"kept byte for byte"| raw
    raw -->|"convert: nothing corrected,<br/>nothing dropped"| tab
    tab ==>|"label, flag, correct;<br/>only exact duplicates dropped"| cln
    cln ==>|"a whole new version<br/>or nothing"| ver
    ver ==>|"reader pins a version"| api
    api -->|"results arrive as"| arrow
    ver -->|"same pinned versions"| duck
    ver -->|"same pinned versions"| pol
    classDef data fill:#dbeafe,stroke:#1d4ed8,color:#0b1220
    classDef step fill:#f1f5f9,stroke:#475569,color:#0b1220
    classDef gate fill:#fef3c7,stroke:#b45309,color:#0b1220
    classDef out  fill:#dcfce7,stroke:#15803d,color:#0b1220
    classDef ext  fill:#f8fafc,stroke:#94a3b8,color:#0b1220,stroke-dasharray:4 3
    classDef key  fill:#ede9fe,stroke:#6d28d9,color:#0b1220,stroke-width:2px
    class src ext
    class raw,tab data
    class cln,ver key
    class api step
    class arrow,duck,pol out
```

Where in the code: closed source, not in this repository; each step is described in [data-model.md](data-model.md).

## 2. Versioned publish under concurrent readers and writers

Writers publish a whole version or nothing while readers keep the version they pinned, as the concurrency gate exercised it ([results](results.md#concurrency)).

```mermaid
sequenceDiagram
    participant R as 12 readers
    participant D as Versioned dataset
    participant W as 4 writers
    participant P as A fifth process
    R->>D: pin the version each started with
    par writers append
        W->>D: publish a whole new version, or nothing
    and a partition is rewritten
        P->>D: rewrite one partition
    and readers keep reading
        R->>D: read through DuckDB, Apache Arrow<br/>and the query interface
        D-->>R: the pinned version, even while<br/>a writer publishes the next one
    end
    Note over R,P: Gate result: 23/23 commits, 0 lost, no writer errors.<br/>1,111 reads, 0 mismatches against the pinned version.<br/>Final dataset: 420,000 rows exactly, every writer's batch once.
```

Where in the code: closed source, not in this repository; the gate is described in [reliability.md](reliability.md#concurrency-tested-rather-than-argued).

## 3. Three layers: what changes each one

What each layer holds, what is allowed to change it, and the one kind of row cleansing removes.

```mermaid
flowchart LR
    src["Market data<br/>as delivered"]
    subgraph layers["Three layers"]
        raw[("raw<br/>byte for byte,<br/>never changed")]
        tab[("typed Parquet<br/>the same rows, typed")]
        cln[("cleansed<br/>labels, flags,<br/>corrected values")]
    end
    dup["exact duplicates:<br/>the only rows removed"]
    ctl{{"checked against<br/>control days"}}
    src -->|"kept as it arrived"| raw
    raw -->|"the converter,<br/>once per raw file"| tab
    tab ==>|"one reviewed cleansing<br/>program per table"| cln
    tab -->|"removed: 0.09%<br/>of A-share rows"| dup
    cln -.->|"compared with typed:<br/>shows what each rule changed"| tab
    cln -->|"each rule's hits<br/>counted per day"| ctl
    classDef data fill:#dbeafe,stroke:#1d4ed8,color:#0b1220
    classDef step fill:#f1f5f9,stroke:#475569,color:#0b1220
    classDef gate fill:#fef3c7,stroke:#b45309,color:#0b1220
    classDef out  fill:#dcfce7,stroke:#15803d,color:#0b1220
    classDef ext  fill:#f8fafc,stroke:#94a3b8,color:#0b1220,stroke-dasharray:4 3
    classDef key  fill:#ede9fe,stroke:#6d28d9,color:#0b1220,stroke-width:2px
    class src ext
    class raw,tab data
    class cln key
    class dup,ctl gate
```

Where in the code: closed source, not in this repository; described in [data-model.md](data-model.md#three-layers).

## 4. Look-ahead refusal

Gap handling that looks only backwards is allowed; one that would read the future is refused unless the caller opts in.

```mermaid
flowchart LR
    req["a request with<br/>gaps to fill"]
    dir{{"does the gap handling<br/>look forwards?"}}
    opt{{"explicit opt-in<br/>given?"}}
    ref["refused"]
    rows["rows returned;<br/>every filled row<br/>says it was filled"]
    req -->|"gap handling named<br/>in the call"| dir
    dir ==>|"no: looks only<br/>backwards, allowed"| rows
    dir -->|"yes: it would<br/>read the future"| opt
    opt -->|"no"| ref
    opt -->|"yes"| rows
    classDef data fill:#dbeafe,stroke:#1d4ed8,color:#0b1220
    classDef step fill:#f1f5f9,stroke:#475569,color:#0b1220
    classDef gate fill:#fef3c7,stroke:#b45309,color:#0b1220
    classDef out  fill:#dcfce7,stroke:#15803d,color:#0b1220
    classDef ext  fill:#f8fafc,stroke:#94a3b8,color:#0b1220,stroke-dasharray:4 3
    classDef key  fill:#ede9fe,stroke:#6d28d9,color:#0b1220,stroke-width:2px
    class req step
    class dir,opt gate
    class ref gate
    class rows out
```

Where in the code: closed source, not in this repository; described in [data-model.md](data-model.md#one-interface-wherever-a-researcher-works).

## 5. The alerting incident: detection worked, delivery did not

Before the fix, every failure was detected and written to a log nobody read; after it, a fault reaches a person once when it starts and once when it clears.

```mermaid
flowchart LR
    subgraph before["Before: 13 days to 2026-09-05"]
        direction TB
        hc1["scheduled health check,<br/>every ten minutes"]
        log1[("failure log<br/>29,754 unread lines")]
        nob["nobody"]
        rej["rejected fix: muted within<br/>a minute, as blind as before"]
        hc1 -->|"detection worked:<br/>each failure written"| log1
        log1 -.->|"delivery did not exist"| nob
        log1 -.->|"forward the log as it is:<br/>one message per line"| rej
    end
    subgraph after["After: built 2026-09-05 to 2026-10-03"]
        direction TB
        hc2["the checks"]
        al["alerter: remembered state,<br/>heartbeat on every run,<br/>every read bounded"]
        wat["second, independent<br/>watcher"]
        per["a person"]
        hc2 -->|"a fault starts<br/>or clears"| al
        al ==>|"one message when it starts,<br/>one when it clears"| per
        wat ==>|"raises the alarm if the<br/>regular check-in stops"| per
    end
    before ==>|"delivery built,<br/>detection kept"| after
    classDef data fill:#dbeafe,stroke:#1d4ed8,color:#0b1220
    classDef step fill:#f1f5f9,stroke:#475569,color:#0b1220
    classDef gate fill:#fef3c7,stroke:#b45309,color:#0b1220
    classDef out  fill:#dcfce7,stroke:#15803d,color:#0b1220
    classDef ext  fill:#f8fafc,stroke:#94a3b8,color:#0b1220,stroke-dasharray:4 3
    classDef key  fill:#ede9fe,stroke:#6d28d9,color:#0b1220,stroke-width:2px
    class hc1,hc2 step
    class log1 data
    class nob ext
    class rej gate
    class al key
    class wat step
    class per out
```

Where in the code: closed source, not in this repository; the incident is told in [reliability.md](reliability.md#incident-thirteen-days-of-failures-that-reached-nobody).
