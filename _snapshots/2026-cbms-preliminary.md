---
snapshot_id: 2026-cbms-preliminary
label: "CBMS conference runs - one run per pair, legacy schema"
status: preliminary
generated_utc: "2026-09-01"
kit_version: "0.2.0"
replicate_kind: unknown
title: "Snapshot 2026-cbms-preliminary"
---

These are the runs behind the DeepECG-Kit conference paper, republished here in full.

**Read them as preliminary.** Every cell is a single training run. The runs predate the
current metrics schema, so they carry no seed, no `average` column and no calibration
metrics. `deepecg aggregate` was given `--include-legacy`, which pools seedless runs under
a sentinel replicate id of `-1`; the manifest records that, and the site refuses to present
a snapshot built that way as `current`.

### What differs from the paper

The paper omitted architectures that failed to converge on a given task. This snapshot does
not: ConvNeXt-V2 on MIT-BIH AFDB is published at its measured F1 of **0.000**, with
precision and recall also zero, flagged *zero predicted positives*. An omitted failure and a
measured failure are different claims, and only one of them is honest about what happened.

### What was excluded, and why

The source run directory contains a `_/` subdirectory holding an earlier MIT-BIH protocol
that used a sample-level rather than a recording-level split. Those runs score much higher
(ResNet1D F1 0.991 against 0.950 under the grouped split) and are superseded, not merely
older. They are excluded by building the snapshot non-recursively.

This matters more than it looks. Both directories hold a run for the same
`(model, dataset)` and neither carries a seed, so including both collapses them onto one key
and `deepecgkit` resolves the collision by **filesystem mtime** &mdash; which `cp`, `clone`
and `rsync` all destroy. Two people running the same documented command could publish
different numbers. `tools/make_snapshot.py` refuses to proceed on a duplicate unless it is
accepted explicitly.

### Known defects

`unified-af` results from this snapshot carry a defect entry: accuracy 0.9985 and MCC 0.9840
against a macro-F1 of 0.8646 is the signature of a leaking or catastrophically imbalanced
split, not of a strong model. The task is marked *exploratory* and its numbers should not be
cited.
