---
registry_name: xresnet1d101
title: xResNet1D-101
family: cnn
order: 117
maturity: reference
one_liner: The deep xResNet1d of the PTB-XL benchmark, built from bottleneck blocks.
search_keywords: xresnet1d101 xresnet 101 bottleneck ptbxl benchmark strodthoff concat pooling deep
origin:
  paper_title: 'Deep Learning for ECG Analysis: Benchmarks and Insights from PTB-XL'
  authors: Strodthoff, Wagner, Schaeffter, Samek
  venue: IEEE JBHI
  year: 2021
  doi: 10.1109/JBHI.2020.3022989
  code_url: https://github.com/helme/ecg_ptbxl_benchmarking
  adapted_from: xresnet1d-benchmark
implementation_notes: 'Follows the xresnet1d101 constructor of the PTB-XL benchmark code, so PTB-XL numbers
  stay comparable with Strodthoff et al. The fixed-width xresnet1d-benchmark is its shallow counterpart.

  '
applicability:
  gradient_attribution: true
  occlusion: true
  class_activation: false
  notes: null
sections:
- type: description
  title: Overview
  body: 'The deep xResNet1d of the PTB-XL benchmark: bottleneck residual blocks, a

    three-convolution stem and a concatenated average-and-maximum pooling head.

    '
- type: architecture
  title: Architecture
- type: results
  title: Benchmark results
- type: code
  title: Training this architecture
  language: bash
  body: 'deepecg train -m xresnet1d101 -d ptbxl --multi-label --seed 42

    '
- type: links
  title: References
  items:
  - label: 'Deep Learning for ECG Analysis: Benchmarks and Insights from PTB-XL'
    url: https://doi.org/10.1109/JBHI.2020.3022989
  - label: Reference implementation
    url: https://github.com/helme/ecg_ptbxl_benchmarking
deviations_from_paper: []
---
