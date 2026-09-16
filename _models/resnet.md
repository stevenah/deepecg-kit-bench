---
registry_name: resnet
title: ResNet1D
family: cnn
order: 112
maturity: reference
one_liner: A 1D adaptation of the standard residual network, and the project's default trunk.
search_keywords: resnet resnet1d residual skip connection default
origin:
  paper_title: Deep Residual Learning for Image Recognition
  authors: He, Zhang, Ren, Sun
  venue: CVPR
  year: 2016
  doi: 10.1109/CVPR.2016.90
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
  body: 'A 1D adaptation of the standard residual network, and the project''s default trunk.

    '
- type: architecture
  title: Architecture
- type: results
  title: Benchmark results
- type: code
  title: Training this architecture
  language: bash
  body: 'deepecg train -m resnet -d ptbxl --multi-label --seed 42

    '
- type: links
  title: References
  items:
  - label: Deep Residual Learning for Image Recognition
    url: https://doi.org/10.1109/CVPR.2016.90
implementation_notes: null
deviations_from_paper: []
---
