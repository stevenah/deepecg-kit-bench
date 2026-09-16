---
registry_name: kanres-deep
title: KAN-ResNet (deep)
family: cnn
order: 108
maturity: experimental
one_liner: 'A deeper KAN-ResNet: more residual stages, a narrower final feature dimension.'
search_keywords: kan kolmogorov arnold deep spline residual
origin:
  paper_title: 'KAN: Kolmogorov-Arnold Networks'
  authors: Liu, Wang, Vaidya, Ruehle, Halverson, Soljacic, Hou, Tegmark
  venue: null
  year: 2024
  doi: arXiv:2404.19756
  code_url: null
  adapted_from: kanres
applicability:
  gradient_attribution: true
  occlusion: true
  class_activation: false
  notes: null
sections:
- type: description
  title: Overview
  body: 'A deeper KAN-ResNet: more residual stages, a narrower final feature dimension.

    '
- type: architecture
  title: Architecture
- type: results
  title: Benchmark results
- type: code
  title: Training this architecture
  language: bash
  body: 'deepecg train -m kanres-deep -d ptbxl --multi-label --seed 42

    '
- type: links
  title: References
  items:
  - label: 'KAN: Kolmogorov-Arnold Networks'
    url: https://arxiv.org/abs/2404.19756
implementation_notes: null
deviations_from_paper: []
---
