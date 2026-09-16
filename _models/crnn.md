---
registry_name: crnn
title: CRNN
family: hybrid
order: 318
maturity: reference
one_liner: Convolutional feature extraction followed by an LSTM that aggregates over time.
search_keywords: crnn cnn lstm hybrid recurrent aggregation
origin:
  paper_title: null
  authors: null
  venue: null
  year: null
  doi: null
  code_url: null
  adapted_from: null
implementation_notes: 'A conventional CNN-RNN hybrid rather than a specific published architecture; the
  convolutional front end and recurrent aggregator are both standard.

  '
applicability:
  gradient_attribution: true
  occlusion: true
  class_activation: false
  notes: null
sections:
- type: description
  title: Overview
  body: 'Convolutional feature extraction followed by an LSTM that aggregates over time.

    '
- type: architecture
  title: Architecture
- type: results
  title: Benchmark results
- type: code
  title: Training this architecture
  language: bash
  body: deepecg train -m crnn -d ptbxl --multi-label --seed 42
deviations_from_paper: []
---
