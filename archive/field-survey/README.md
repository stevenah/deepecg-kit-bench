# Field survey (archived)

Until October 2026 the site also listed ECG deep-learning architectures that DeepECG-Kit does
not implement, with values reported in their papers. The page now covers the kit's own
architectures only, and these two files are kept here unchanged so the curation is not lost.

| File | Contents |
|---|---|
| `field.yml` | 160 architectures from the literature: title, family, year, reported size, verified DOI or arXiv id |
| `reported.yml` | 18 paper-reported values from 5 papers, each with a note on the paper's protocol |

Nothing reads these files and nothing in `site/` is built from them. The header comments in both
describe tooling that has since been removed (`tools/validate.py`, `make identifiers`, `_models/`,
`_data/`); it is in the git history before this directory was created.
