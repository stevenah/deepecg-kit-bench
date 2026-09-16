---
task_id: mitbih-afdb-binary
title: MIT-BIH AFDB — binary AF detection
short_title: MIT-BIH AFDB
registry_dataset: mitbih-afdb
order: 3
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
dataset_url: https://physionet.org/content/afdb/1.0.0/
replicate_note: 'The journal protocol specifies grouped five-fold cross-validation over recordings for
  this task. The committed replicates are random seeds over a fixed grouped split, because run_metadata.json
  has no fold field to record one. Read the dispersion as training stochasticity only -- it is not between-recording
  variance.

  '
split_protocol: 'Grouped split over recordings: segments from one recording never cross a split boundary.
  An earlier sample-level protocol produced much higher scores and is superseded; see the snapshot notes.

  '
summary: Long two-lead Holter recordings. The dataset registers four rhythm classes, but this task collapses
  them to AF versus non-AF, so precision, recall and F1 are positive-class values rather than macro averages.
ecgbench_url: null
---
