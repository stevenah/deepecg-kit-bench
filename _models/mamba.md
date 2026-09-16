---
registry_name: mamba
title: Mamba-1D
family: ssm
order: 521
maturity: experimental
one_liner: Bidirectional selective state-space model with sub-quadratic mixing over long sequences.
search_keywords: mamba state space ssm selective bidirectional linear
origin:
  paper_title: 'Mamba: Linear-Time Sequence Modeling with Selective State Spaces'
  authors: Gu, Dao
  venue: null
  year: 2023
  doi: arXiv:2312.00752
  code_url: null
  adapted_from: null
implementation_notes: 'Included here because it is a registered architecture with measured results. Note
  the conference paper excludes Mamba; this site documents the library, not the paper.

  '
applicability:
  gradient_attribution: true
  occlusion: true
  class_activation: false
  notes: null
sections:
- type: description
  title: Overview
  body: 'Bidirectional selective state-space model with sub-quadratic mixing over long

    sequences.

    '
- type: architecture
  title: Architecture
- type: results
  title: Benchmark results
- type: code
  title: Training this architecture
  language: bash
  body: 'deepecg train -m mamba -d ptbxl --multi-label --seed 42

    '
- type: links
  title: References
  items:
  - label: 'Mamba: Linear-Time Sequence Modeling with Selective State Spaces'
    url: https://arxiv.org/abs/2312.00752
deviations_from_paper: []
---
