---
registry_name: afmodel
title: AFModel
family: cnn
order: 110
maturity: experimental
one_liner: A convolutional classifier shaped for fixed 30-second single-lead segments.
search_keywords: af model 30s segment atrial fibrillation recording length
origin:
  paper_title: null
  authors: null
  venue: null
  year: null
  doi: null
  code_url: null
  adapted_from: null
implementation_notes: 'Carries default_kwargs {''recording_length'': 30} and a minimum input length of
  7971 samples, so it is the one architecture that cannot accept an arbitrarily short window.

  '
applicability:
  gradient_attribution: true
  occlusion: true
  class_activation: false
  notes: null
sections:
- type: description
  title: Overview
  body: 'A convolutional classifier shaped for fixed 30-second single-lead segments.

    '
- type: architecture
  title: Architecture
- type: results
  title: Benchmark results
- type: code
  title: Training this architecture
  language: bash
  body: deepecg train -m afmodel -d ptbxl --multi-label --seed 42
deviations_from_paper: []
---
