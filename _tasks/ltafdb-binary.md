---
task_id: ltafdb-binary
title: LTAFDB — binary AF detection
short_title: LTAFDB
registry_dataset: ltafdb
order: 4
in_journal: true
scope: primary
label_mode: binary
expected_averaging: binary
replicate_kind: seed
expected_replicates: 5
primary_metric: f1
probe:
  input_channels: 2
  output_size: 2
dataset_url: https://physionet.org/content/ltafdb/1.0.0/
replicate_note: 'As for MIT-BIH AFDB, the journal specifies grouped five-fold cross-validation over recordings
  and the library cannot record a fold id.

  '
split_protocol: 'Grouped split over recordings.

  '
summary: The Long-Term AF Database. Named as a benchmark task by the journal protocol, but experiments.yaml
  currently defines no LTAFDB sweep, so every cell in this task is "not run". It is listed rather than
  hidden so the gap is visible.
ecgbench_url: null
---
