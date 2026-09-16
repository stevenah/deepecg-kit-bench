---
registry_name: dualnet
title: ECG-DualNet
family: hybrid
order: 317
maturity: experimental
one_liner: Two parallel branches -- a CNN-LSTM path and a transformer path -- fused before the head.
search_keywords: dualnet dual path cnn lstm transformer fusion
origin:
  paper_title: null
  authors: null
  venue: null
  year: null
  doi: null
  code_url: null
  adapted_from: null
implementation_notes: 'Bounded above at 5000 input samples by the transformer branch''s positional encoding.

  '
applicability:
  gradient_attribution: true
  occlusion: true
  class_activation: false
  notes: null
sections:
- type: description
  title: Overview
  body: 'Two parallel branches -- a CNN-LSTM path and a transformer path -- fused before the

    head.

    '
- type: architecture
  title: Architecture
- type: results
  title: Benchmark results
- type: code
  title: Training this architecture
  language: bash
  body: deepecg train -m dualnet -d ptbxl --multi-label --seed 42
deviations_from_paper: []
---
