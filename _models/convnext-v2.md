---
registry_name: convnext-v2
title: ConvNeXt-V2
family: cnn
order: 111
maturity: reference
one_liner: Depthwise convolutions with global response normalisation, adapted to one dimension.
search_keywords: convnext grn depthwise modern convnet
origin:
  paper_title: 'ConvNeXt V2: Co-designing and Scaling ConvNets with Masked Autoencoders'
  authors: Woo, Debnath, Hu, Chen, Liu, Kweon, Xie
  venue: CVPR
  year: 2023
  doi: null
  code_url: https://github.com/facebookresearch/ConvNeXt-V2
  adapted_from: null
implementation_notes: 'Adapted from the 2D vision architecture; the masked-autoencoder pretraining that
  motivates GRN is not used here, so the block is trained from scratch.

  '
applicability:
  gradient_attribution: true
  occlusion: true
  class_activation: false
  notes: null
sections:
- type: description
  title: Overview
  body: 'Depthwise convolutions with global response normalisation, adapted to one dimension.

    '
- type: architecture
  title: Architecture
- type: results
  title: Benchmark results
- type: code
  title: Training this architecture
  language: bash
  body: 'deepecg train -m convnext-v2 -d ptbxl --multi-label --seed 42

    '
- type: links
  title: References
  items:
  - label: Reference implementation
    url: https://github.com/facebookresearch/ConvNeXt-V2
deviations_from_paper: []
---
