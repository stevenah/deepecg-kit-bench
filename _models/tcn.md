---
registry_name: tcn
title: TCN
family: cnn
order: 109
maturity: experimental
one_liner: Dilated causal convolutions giving an exponentially growing receptive field.
search_keywords: tcn temporal convolutional dilated causal receptive field
origin:
  paper_title: An Empirical Evaluation of Generic Convolutional and Recurrent Networks for Sequence Modeling
  authors: Bai, Kolter, Koltun
  venue: null
  year: 2018
  doi: arXiv:1803.01271
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
  body: 'Dilated causal convolutions giving an exponentially growing receptive field.

    '
- type: architecture
  title: Architecture
- type: results
  title: Benchmark results
- type: code
  title: Training this architecture
  language: bash
  body: 'deepecg train -m tcn -d ptbxl --multi-label --seed 42

    '
- type: links
  title: References
  items:
  - label: An Empirical Evaluation of Generic Convolutional and Recurrent Networks for Sequence Modeling
    url: https://arxiv.org/abs/1803.01271
implementation_notes: null
deviations_from_paper: []
---
