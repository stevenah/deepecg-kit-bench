---
registry_name: gru
title: GRU
family: rnn
order: 216
maturity: experimental
one_liner: A gated recurrent baseline; cheaper per step than LSTM with a comparable role.
search_keywords: gru gated recurrent unit sequence
origin:
  paper_title: Learning Phrase Representations using RNN Encoder-Decoder for Statistical Machine Translation
  authors: Cho, van Merrienboer, Gulcehre, Bahdanau, Bougares, Schwenk, Bengio
  venue: EMNLP
  year: 2014
  doi: arXiv:1406.1078
  code_url: null
  adapted_from: null
applicability:
  gradient_attribution: true
  occlusion: true
  class_activation: false
  notes: null
sections:
- type: description
  title: Overview
  body: 'A gated recurrent baseline; cheaper per step than LSTM with a comparable role.

    '
- type: architecture
  title: Architecture
- type: results
  title: Benchmark results
- type: code
  title: Training this architecture
  language: bash
  body: 'deepecg train -m gru -d ptbxl --multi-label --seed 42

    '
- type: links
  title: References
  items:
  - label: Learning Phrase Representations using RNN Encoder-Decoder for Statistical Machine Translation
    url: https://arxiv.org/abs/1406.1078
implementation_notes: null
deviations_from_paper: []
---
