---
registry_name: transformer
title: Transformer
family: attention
order: 419
maturity: experimental
one_liner: A transformer encoder over timesteps with learned positional encoding.
search_keywords: transformer attention encoder positional encoding
origin:
  paper_title: Attention Is All You Need
  authors: Vaswani, Shazeer, Parmar, Uszkoreit, Jones, Gomez, Kaiser, Polosukhin
  venue: NeurIPS
  year: 2017
  doi: arXiv:1706.03762
  code_url: null
  adapted_from: null
implementation_notes: 'Positional encoding caps the input at 5000 samples, which is the whole 10-second
  PTB- XL record at 500 Hz and a fraction of a Holter recording.

  '
applicability:
  gradient_attribution: true
  occlusion: true
  class_activation: false
  notes: null
sections:
- type: description
  title: Overview
  body: 'A transformer encoder over timesteps with learned positional encoding.

    '
- type: architecture
  title: Architecture
- type: results
  title: Benchmark results
- type: code
  title: Training this architecture
  language: bash
  body: 'deepecg train -m transformer -d ptbxl --multi-label --seed 42

    '
- type: links
  title: References
  items:
  - label: Attention Is All You Need
    url: https://arxiv.org/abs/1706.03762
deviations_from_paper: []
---
