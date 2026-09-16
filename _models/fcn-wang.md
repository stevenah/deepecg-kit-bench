---
registry_name: fcn-wang
title: FCN-Wang
family: cnn
order: 103
maturity: reference
one_liner: Fully convolutional network with global average pooling and no fully-connected trunk.
search_keywords: fcn wang fully convolutional gap strong baseline time series
origin:
  paper_title: 'Time Series Classification from Scratch with Deep Neural Networks: A Strong Baseline'
  authors: Wang, Yan, Oates
  venue: IJCNN
  year: 2017
  doi: 10.1109/IJCNN.2017.7966039
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
  body: 'Fully convolutional network with global average pooling and no fully-connected

    trunk.

    '
- type: architecture
  title: Architecture
- type: results
  title: Benchmark results
- type: code
  title: Training this architecture
  language: bash
  body: 'deepecg train -m fcn-wang -d ptbxl --multi-label --seed 42

    '
- type: links
  title: References
  items:
  - label: 'Time Series Classification from Scratch with Deep Neural Networks: A Strong Baseline'
    url: https://doi.org/10.1109/IJCNN.2017.7966039
implementation_notes: null
deviations_from_paper: []
---
