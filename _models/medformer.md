---
registry_name: medformer
title: Medformer
family: attention
order: 420
maturity: experimental
one_liner: Multi-granularity patching transformer built for medical time series.
search_keywords: medformer patching multi-granularity transformer medical time series
origin:
  paper_title: 'Medformer: A Multi-Granularity Patching Transformer for Medical Time-Series Classification'
  authors: Wang, Chen, Fu, Song, Zhang, Wang, Yang, Wang
  venue: NeurIPS
  year: 2024
  doi: arXiv:2405.19363
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
  body: 'Multi-granularity patching transformer built for medical time series.

    '
- type: architecture
  title: Architecture
- type: results
  title: Benchmark results
- type: code
  title: Training this architecture
  language: bash
  body: 'deepecg train -m medformer -d ptbxl --multi-label --seed 42

    '
- type: links
  title: References
  items:
  - label: 'Medformer: A Multi-Granularity Patching Transformer for Medical Time-Series Classification'
    url: https://arxiv.org/abs/2405.19363
implementation_notes: null
deviations_from_paper: []
---
