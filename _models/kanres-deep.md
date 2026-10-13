---
registry_name: kanres-deep
title: KanRes-Deep
family: cnn
order: 108
maturity: experimental
one_liner: 'The deep KanRes variant: more residual blocks, a narrower final feature dimension.'
search_keywords: kanres kanres-deep residual deep hicks explainable
origin:
  paper_title: Explaining deep neural networks for knowledge discovery in electrocardiogram analysis
  authors: Hicks, Isaksen, Thambawita, Ghouse, Ahlberg, Linneberg, Grarup, Strümke, Ellervik, Olesen, Hansen,
    Graff, Holstein-Rathlou, Halvorsen, Maleckar, Riegler, Kanters
  venue: Scientific Reports
  year: 2021
  doi: 10.1038/s41598-021-90285-5
  code_url: null
  adapted_from: kanres
applicability:
  gradient_attribution: true
  occlusion: true
  class_activation: false
  notes: null
sections:
- type: description
  title: Overview
  body: 'The deep KanRes variant: more residual blocks, a narrower final feature dimension.

    '
- type: architecture
  title: Architecture
- type: results
  title: Benchmark results
- type: code
  title: Training this architecture
  language: bash
  body: 'deepecg train -m kanres-deep -d ptbxl --multi-label --seed 42

    '
- type: links
  title: References
  items:
  - label: Explaining deep neural networks for knowledge discovery in electrocardiogram analysis
    url: https://doi.org/10.1038/s41598-021-90285-5
implementation_notes: null
deviations_from_paper: []
---
