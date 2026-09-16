---
registry_name: xresnet
title: xResNet1D
family: cnn
order: 113
maturity: reference
one_liner: 'ResNet with the bag-of-tricks refinements: Mish activation and blur-pool downsampling.'
search_keywords: xresnet mish blurpool bag of tricks
origin:
  paper_title: Bag of Tricks for Image Classification with Convolutional Neural Networks
  authors: He, Zhang, Zhang, Zhang, Xie, Li
  venue: CVPR
  year: 2019
  doi: 10.1109/CVPR.2019.00065
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
  body: 'ResNet with the bag-of-tricks refinements: Mish activation and blur-pool

    downsampling.

    '
- type: architecture
  title: Architecture
- type: results
  title: Benchmark results
- type: code
  title: Training this architecture
  language: bash
  body: 'deepecg train -m xresnet -d ptbxl --multi-label --seed 42

    '
- type: links
  title: References
  items:
  - label: Bag of Tricks for Image Classification with Convolutional Neural Networks
    url: https://doi.org/10.1109/CVPR.2019.00065
implementation_notes: null
deviations_from_paper: []
---
