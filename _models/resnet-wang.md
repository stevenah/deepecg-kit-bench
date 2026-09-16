---
registry_name: resnet-wang
title: ResNet-Wang
family: cnn
order: 105
maturity: reference
one_liner: 'The residual baseline from the same paper as FCN-Wang: three residual blocks over raw signal.'
search_keywords: resnet wang residual time series baseline
origin:
  paper_title: 'Time Series Classification from Scratch with Deep Neural Networks: A Strong Baseline'
  authors: Wang, Yan, Oates
  venue: IJCNN
  year: 2017
  doi: 10.1109/IJCNN.2017.7966039
  code_url: null
  adapted_from: fcn-wang
applicability:
  gradient_attribution: true
  occlusion: true
  class_activation: false
  notes: null
sections:
- type: description
  title: Overview
  body: 'The residual baseline from the same paper as FCN-Wang: three residual blocks over

    raw signal.

    '
- type: architecture
  title: Architecture
- type: results
  title: Benchmark results
- type: code
  title: Training this architecture
  language: bash
  body: 'deepecg train -m resnet-wang -d ptbxl --multi-label --seed 42

    '
- type: links
  title: References
  items:
  - label: 'Time Series Classification from Scratch with Deep Neural Networks: A Strong Baseline'
    url: https://doi.org/10.1109/IJCNN.2017.7966039
implementation_notes: null
deviations_from_paper: []
---
