---
registry_name: simple-cnn
title: Simple CNN
family: cnn
order: 102
maturity: experimental
one_liner: A short stack of convolution-pooling blocks, used as the cheapest sanity baseline.
search_keywords: simple cnn baseline lightweight fast
origin:
  paper_title: null
  authors: null
  venue: null
  year: null
  doi: null
  code_url: null
  adapted_from: null
implementation_notes: 'No published origin: a minimal in-house baseline whose purpose is to make a training
  pipeline fail loudly rather than to compete.

  '
applicability:
  gradient_attribution: true
  occlusion: true
  class_activation: false
  notes: null
sections:
- type: description
  title: Overview
  body: 'A short stack of convolution-pooling blocks, used as the cheapest sanity baseline.

    '
- type: architecture
  title: Architecture
- type: results
  title: Benchmark results
- type: code
  title: Training this architecture
  language: bash
  body: deepecg train -m simple-cnn -d ptbxl --multi-label --seed 42
deviations_from_paper: []
---
