---
registry_name: kanres
title: KAN-ResNet
family: cnn
order: 101
maturity: experimental
one_liner: A residual trunk whose head uses Kolmogorov-Arnold layers with learned spline activations.
search_keywords: kan kolmogorov arnold spline residual wide
origin:
  paper_title: 'KAN: Kolmogorov-Arnold Networks'
  authors: Liu, Wang, Vaidya, Ruehle, Halverson, Soljacic, Hou, Tegmark
  venue: null
  year: 2024
  doi: arXiv:2404.19756
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
  body: 'A residual trunk whose head uses Kolmogorov-Arnold layers with learned spline

    activations.

    '
- type: architecture
  title: Architecture
- type: results
  title: Benchmark results
- type: code
  title: Training this architecture
  language: bash
  body: 'deepecg train -m kanres -d ptbxl --multi-label --seed 42

    '
- type: links
  title: References
  items:
  - label: 'KAN: Kolmogorov-Arnold Networks'
    url: https://arxiv.org/abs/2404.19756
implementation_notes: null
deviations_from_paper: []
---
