---
registry_name: rocket
title: ROCKET
family: baseline
order: 1
maturity: reference
one_liner: Frozen random convolution kernels summarised by two statistics each, with a linear classifier on top.
search_keywords: rocket random convolutional kernels ppv linear classifier non-deep baseline dempster
origin:
  paper_title: 'ROCKET: exceptionally fast and accurate time series classification using random convolutional
    kernels'
  authors: Dempster, Petitjean, Webb
  venue: Data Mining and Knowledge Discovery
  year: 2020
  doi: 10.1007/s10618-020-00701-z
  code_url: https://github.com/angus924/rocket
  adapted_from: null
implementation_notes: 'Only the linear classifier is trained, so the parameter count covers that layer
  alone. The random kernels are frozen buffers saved with the checkpoint, which keeps a run reproducible.

  '
applicability:
  gradient_attribution: true
  occlusion: true
  class_activation: false
  notes: null
sections:
- type: description
  title: Overview
  body: 'A non-deep baseline. Random convolution kernels are drawn once and never trained; each

    contributes the proportion of positive values and the maximum of its output, and a linear

    layer classifies the resulting feature vector.

    '
- type: architecture
  title: Architecture
- type: results
  title: Benchmark results
- type: code
  title: Training this architecture
  language: bash
  body: 'deepecg train -m rocket -d ptbxl --multi-label --seed 42

    '
- type: links
  title: References
  items:
  - label: 'ROCKET: exceptionally fast and accurate time series classification using random convolutional
      kernels'
    url: https://doi.org/10.1007/s10618-020-00701-z
  - label: Reference implementation
    url: https://github.com/angus924/rocket
deviations_from_paper:
- Every kernel sees all input channels.
- Every kernel uses "same" padding, where the original draws the padding at random.
- The linear classifier is fitted by gradient descent on the training loss, where the original
  fits a ridge regression.
---
