---
registry_name: spectrogram-cnn
title: Spectrogram CNN
family: cnn
order: 115
maturity: experimental
one_liner: A 2-D convolutional network over the log-magnitude spectrogram of each lead.
search_keywords: spectrogram cnn stft time-frequency 2d convolution log magnitude
origin:
  paper_title: null
  authors: null
  venue: null
  year: null
  doi: null
  code_url: null
  adapted_from: null
implementation_notes: 'An in-house design without a published reference implementation. It follows the
  spectrogram-input approach common among entries to the PhysioNet/CinC 2017 challenge.

  '
applicability:
  gradient_attribution: true
  occlusion: true
  class_activation: false
  notes: null
sections:
- type: description
  title: Overview
  body: 'A time-frequency baseline. Each lead is transformed by a short-time Fourier transform

    and its log-magnitude spectrogram forms one image channel; four 2-D convolution blocks and

    global average pooling follow.

    '
- type: architecture
  title: Architecture
- type: results
  title: Benchmark results
- type: code
  title: Training this architecture
  language: bash
  body: 'deepecg train -m spectrogram-cnn -d ptbxl --multi-label --seed 42

    '
deviations_from_paper: []
---
