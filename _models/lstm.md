---
registry_name: lstm
title: LSTM
family: rnn
order: 215
maturity: experimental
one_liner: A recurrent baseline reading the downsampled signal as a sequence.
search_keywords: lstm recurrent sequence gate memory
origin:
  paper_title: Long Short-Term Memory
  authors: Hochreiter, Schmidhuber
  venue: Neural Computation
  year: 1997
  doi: 10.1162/neco.1997.9.8.1735
  code_url: null
  adapted_from: null
applicability:
  gradient_attribution: true
  occlusion: true
  class_activation: false
  notes: null
sections:
- type: description
  title: Overview
  body: 'A recurrent baseline reading the downsampled signal as a sequence.

    '
- type: architecture
  title: Architecture
- type: results
  title: Benchmark results
- type: code
  title: Training this architecture
  language: bash
  body: 'deepecg train -m lstm -d ptbxl --multi-label --seed 42

    '
- type: links
  title: References
  items:
  - label: Long Short-Term Memory
    url: https://doi.org/10.1162/neco.1997.9.8.1735
implementation_notes: null
deviations_from_paper: []
---
