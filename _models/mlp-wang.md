---
registry_name: mlp-wang
title: MLP-Wang
family: baseline
order: 2
maturity: reference
one_liner: 'The fully connected baseline from the same paper as FCN-Wang: three hidden layers over the
  flattened signal.'
search_keywords: mlp wang multilayer perceptron fully connected dense time series baseline
origin:
  paper_title: 'Time Series Classification from Scratch with Deep Neural Networks: A Strong Baseline'
  authors: Wang, Yan, Oates
  venue: IJCNN
  year: 2017
  doi: 10.1109/IJCNN.2017.7966039
  code_url: null
  adapted_from: null
implementation_notes: null
applicability:
  gradient_attribution: true
  occlusion: true
  class_activation: false
  notes: null
sections:
- type: description
  title: Overview
  body: 'The fully connected baseline of Wang et al.: the signal is flattened and passed through

    three hidden layers with ReLU activations and dropout.

    '
- type: architecture
  title: Architecture
- type: results
  title: Benchmark results
- type: code
  title: Training this architecture
  language: bash
  body: 'deepecg train -m mlp-wang -d ptbxl --multi-label --seed 42

    '
- type: links
  title: References
  items:
  - label: 'Time Series Classification from Scratch with Deep Neural Networks: A Strong Baseline'
    url: https://doi.org/10.1109/IJCNN.2017.7966039
deviations_from_paper:
- The signal is averaged over time to a fixed number of samples per lead before it is flattened,
  so that any signal length is accepted; the original flattens the series as it is.
---
