---
registry_name: deep-res-cnn
title: DeepResCNN
family: cnn
order: 107
maturity: experimental
one_liner: A deep residual network that treats the multi-lead recording as a 2D image.
search_keywords: deep res cnn elyamani 2d residual multi-lead
origin:
  paper_title: Deep residual 2D convolutional neural network for cardiovascular disease classification
  authors: Elyamani, Salem, Melgani, Yhiea
  venue: Scientific Reports
  year: 2024
  doi: 10.1038/s41598-024-72382-3
  code_url: https://github.com/HaneenElyamani/ECG-classification
  adapted_from: null
implementation_notes: 'Operates on a 2D (leads x time) view rather than 1D channels, so lead ordering
  is spatially meaningful to this model in a way it is not for the 1D trunks.

  '
applicability:
  gradient_attribution: true
  occlusion: true
  class_activation: false
  notes: null
sections:
- type: description
  title: Overview
  body: 'A deep residual network that treats the multi-lead recording as a 2D image.

    '
- type: architecture
  title: Architecture
- type: results
  title: Benchmark results
- type: code
  title: Training this architecture
  language: bash
  body: 'deepecg train -m deep-res-cnn -d ptbxl --multi-label --seed 42

    '
- type: links
  title: References
  items:
  - label: Deep residual 2D convolutional neural network for cardiovascular disease classification
    url: https://doi.org/10.1038/s41598-024-72382-3
  - label: Reference implementation
    url: https://github.com/HaneenElyamani/ECG-classification
deviations_from_paper: []
---
