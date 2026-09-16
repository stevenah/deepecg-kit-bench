---
registry_name: inception-time
title: InceptionTime
family: cnn
order: 106
maturity: reference
one_liner: Parallel convolutions at several kernel widths, capturing multi-scale temporal structure.
search_keywords: inception time multi-scale kernel ensemble
origin:
  paper_title: 'InceptionTime: Finding AlexNet for Time Series Classification'
  authors: Fawaz, Lucas, Forestier, Pelletier, Schmidt, Weber, Webb, Idoumghar, Muller, Petitjean
  venue: Data Mining and Knowledge Discovery
  year: 2020
  doi: 10.1007/s10618-020-00710-y
  code_url: https://github.com/hfawaz/InceptionTime
  adapted_from: null
applicability:
  gradient_attribution: true
  occlusion: true
  class_activation: false
  notes: null
sections:
- type: description
  title: Overview
  body: 'Parallel convolutions at several kernel widths, capturing multi-scale temporal

    structure.

    '
- type: architecture
  title: Architecture
- type: results
  title: Benchmark results
- type: code
  title: Training this architecture
  language: bash
  body: 'deepecg train -m inception-time -d ptbxl --multi-label --seed 42

    '
- type: links
  title: References
  items:
  - label: 'InceptionTime: Finding AlexNet for Time Series Classification'
    url: https://doi.org/10.1007/s10618-020-00710-y
  - label: Reference implementation
    url: https://github.com/hfawaz/InceptionTime
implementation_notes: null
deviations_from_paper: []
---
