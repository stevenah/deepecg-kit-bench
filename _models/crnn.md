---
registry_name: crnn
title: CRNN
family: hybrid
order: 318
maturity: reference
one_liner: Convolutional feature extraction followed by an LSTM that aggregates over time.
search_keywords: crnn cnn lstm hybrid recurrent aggregation
origin:
  paper_title: Convolutional Recurrent Neural Networks for Electrocardiogram Classification
  authors: Zihlmann, Perekrestenko, Tschannen
  venue: Computing in Cardiology
  year: 2017
  doi: 10.22489/CinC.2017.070-060
  code_url: null
  adapted_from: null
implementation_notes: 'Follows the convolutional-recurrent design of Zihlmann et al. without reproducing
  their network; the convolutional front end and recurrent aggregator are both standard.

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
- type: links
  title: References
  items:
  - label: Convolutional Recurrent Neural Networks for Electrocardiogram Classification
    url: https://doi.org/10.22489/CinC.2017.070-060
deviations_from_paper:
- Convolves the raw signal, where the original network takes logarithmic spectrograms.
---
