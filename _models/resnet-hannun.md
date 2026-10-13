---
registry_name: resnet-hannun
title: ResNet-Hannun
family: cnn
order: 116
maturity: reference
one_liner: The 34-layer pre-activation residual network of Hannun et al. for rhythm classification.
search_keywords: resnet hannun rajpurkar 34-layer pre-activation residual rhythm arrhythmia ambulatory
  cardiologist-level nature medicine
origin:
  paper_title: Cardiologist-level arrhythmia detection and classification in ambulatory electrocardiograms
    using a deep neural network
  authors: Hannun, Rajpurkar, Haghpanahi, Tison, Bourn, Turakhia, Ng
  venue: Nature Medicine
  year: 2019
  doi: 10.1038/s41591-018-0268-3
  code_url: https://github.com/awni/ecg
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
  body: 'The 34-layer residual network of Hannun et al.: a stem convolution followed by sixteen

    pre-activation residual blocks of two convolutions each, with long kernels and repeated

    subsampling.

    '
- type: architecture
  title: Architecture
- type: results
  title: Benchmark results
- type: code
  title: Training this architecture
  language: bash
  body: 'deepecg train -m resnet-hannun -d ptbxl --multi-label --seed 42

    '
- type: links
  title: References
  items:
  - label: Cardiologist-level arrhythmia detection and classification in ambulatory electrocardiograms
      using a deep neural network
    url: https://doi.org/10.1038/s41591-018-0268-3
  - label: Reference implementation
    url: https://github.com/awni/ecg
deviations_from_paper:
- The original emits one prediction per output step; here the final feature map is pooled over
  time and a single classifier is applied.
---
