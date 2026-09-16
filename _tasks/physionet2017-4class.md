---
task_id: physionet2017-4class
title: PhysioNet 2017 — four-class rhythm
short_title: PhysioNet 2017
registry_dataset: af-classification
order: 2
in_journal: true
scope: primary
label_mode: single_label
expected_averaging: macro
replicate_kind: seed
expected_replicates: 5
primary_metric: f1
probe:
  input_channels: 1
  output_size: 4
dataset_url: https://physionet.org/content/challenge-2017/1.0.0/
split_protocol: 'Random stratified split at the record level. Recordings are single-lead and of variable
  length.

  '
summary: 'Single-lead recordings from the 2017 PhysioNet/CinC Challenge, labelled normal, atrial fibrillation,
  other rhythm, or too noisy to classify. Beware when comparing against the literature: the challenge''s
  own official score is the mean F1 over THREE classes -- normal, AF and other -- with the noisy class
  deliberately excluded from the average, whereas the F1 on this page is macro-averaged over all four.
  A published CinC-2017 score is therefore a different quantity from this one, and systematically higher
  for dropping the rarest and hardest class. No published value may be copied into this task without
  recomputing it over four classes, which the papers do not give enough information to do.'
replicate_note: null
ecgbench_url: null
---
