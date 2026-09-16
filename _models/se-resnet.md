---
registry_name: se-resnet
title: SE-ResNet1D
family: cnn
order: 114
maturity: reference
one_liner: ResNet1D with squeeze-and-excitation blocks recalibrating each channel.
search_keywords: se-resnet seresnet squeeze excitation channel attention
origin:
  paper_title: Squeeze-and-Excitation Networks
  authors: Hu, Shen, Sun
  venue: CVPR
  year: 2018
  doi: 10.1109/CVPR.2018.00745
  code_url: null
  adapted_from: resnet
applicability:
  gradient_attribution: true
  occlusion: true
  class_activation: false
  notes: null
sections:
- type: description
  title: Overview
  body: 'ResNet1D with squeeze-and-excitation blocks recalibrating each channel.

    '
- type: architecture
  title: Architecture
- type: results
  title: Benchmark results
- type: code
  title: Training this architecture
  language: bash
  body: 'deepecg train -m se-resnet -d ptbxl --multi-label --seed 42

    '
- type: links
  title: References
  items:
  - label: Squeeze-and-Excitation Networks
    url: https://doi.org/10.1109/CVPR.2018.00745
implementation_notes: null
deviations_from_paper: []
---
