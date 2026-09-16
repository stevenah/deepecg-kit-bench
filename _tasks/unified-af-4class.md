---
task_id: unified-af-4class
title: Unified AF — cross-source four-class
short_title: Unified AF
registry_dataset: unified-af
order: 5
in_journal: false
scope: exploratory
label_mode: single_label
expected_averaging: macro
replicate_kind: seed
expected_replicates: 5
primary_metric: f1
probe:
  input_channels: 1
  output_size: 4
split_protocol: 'Combined corpus over PhysioNet 2017, MIT-BIH AFDB and LTAFDB. The grouping guarantee
  across the three source datasets has not been audited.

  '
summary: 'A combined corpus spanning three sources. Marked exploratory: it is not one of the journal''s
  four tasks, and its committed numbers carry a known defect -- accuracy and MCC are implausibly high
  relative to macro-F1, which is the signature of a leaking or catastrophically imbalanced split. Do not
  cite these numbers.'
replicate_note: null
dataset_url: null
ecgbench_url: null
---
