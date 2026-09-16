---
registry_name: xresnet1d-benchmark
title: xResNet1D-benchmark
family: cnn
order: 104
maturity: reference
one_liner: The xResNet1d variant used by the PTB-XL benchmark, with a fixed feature dim and concat pooling.
search_keywords: xresnet1d benchmark ptbxl strodthoff concat pooling
origin:
  paper_title: 'Deep Learning for ECG Analysis: Benchmarks and Insights from PTB-XL'
  authors: Strodthoff, Wagner, Schaeffter, Samek
  venue: IEEE JBHI
  year: 2021
  doi: 10.1109/JBHI.2020.3022989
  code_url: https://github.com/helme/ecg_ptbxl_benchmarking
  adapted_from: xresnet
implementation_notes: 'Kept deliberately faithful to the published benchmark configuration so PTB-XL numbers
  stay comparable with Strodthoff et al.

  '
applicability:
  gradient_attribution: true
  occlusion: true
  class_activation: false
  notes: null
sections:
- type: description
  title: Overview
  body: 'The xResNet1d variant used by the PTB-XL benchmark, with a fixed feature dim and

    concat pooling.

    '
- type: architecture
  title: Architecture
- type: results
  title: Benchmark results
- type: code
  title: Training this architecture
  language: bash
  body: 'deepecg train -m xresnet1d-benchmark -d ptbxl --multi-label --seed 42

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
