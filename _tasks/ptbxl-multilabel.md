---
task_id: ptbxl-multilabel
title: PTB-XL — diagnostic superclasses
short_title: PTB-XL
registry_dataset: ptbxl
order: 1
in_journal: true
scope: primary
label_mode: multi_label
expected_averaging: macro-label
replicate_kind: seed
expected_replicates: 5
primary_metric: f1
probe:
  input_channels: 12
  output_size: 5
dataset_url: https://physionet.org/content/ptb-xl/1.0.3/
ecgbench_url: https://vajira.info/ECGBench/datasets/ptb-xl.html
split_protocol: 'Random stratified split at the record level in the committed snapshot. The journal protocol
  specifies the official 10-fold assignment (folds 1-8 train, 9 validation, 10 test) for comparability
  with Strodthoff et al.; the two are not interchangeable.

  '
summary: Twelve-lead resting ECGs labelled with five diagnostic superclasses (NORM, MI, STTC, CD, HYP).
  Records carry more than one superclass, so this is a multi-label task and precision, recall and F1 are
  macro-averaged over labels.
replicate_note: null
---
