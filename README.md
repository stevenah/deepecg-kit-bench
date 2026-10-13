# DeepECG-Bench

The architectures in [DeepECG-Kit](https://github.com/stevenah/deepecg-kit) and their benchmark
results on every task, as one page.

**https://stevenah.github.io/deepecg-kit-bench/**

The model-side counterpart to [ECGBench](https://vajira.info/ECGBench/), which catalogues ECG
*datasets*.

## How it works

`site/` is the whole website and is published as it is; there is no build step.
`site/app.js` has no dependencies: it fetches three data files and draws the table in the
browser.

| File | What it holds | Written by |
|---|---|---|
| `site/data/catalogue.json` | Families, tasks, metric labels, and the prose and reference for each architecture | Hand |
| `site/data/registry.json` | Every machine fact about an architecture: display name, class, parameter counts per input shape | `make registry` |
| `site/data/results.json` | One row per architecture and task, with every metric as `deepecg aggregate` computed it | `make results` |
| `site/plots/<task>/<architecture>/` | Diagnostic plots of the run behind each result | `make results` |

Each file has one writer, and no number is typed by hand: parameter counts come from the
registry export and results from the library's own aggregation.

## Commands

```bash
make serve      # preview at http://localhost:4000/ (PORT=... to change)
make check      # every test
make registry   # re-export registry.json from ../deepecg-kit (needs its venv, with torch)
make results    # publish new results; see below
```

## Updating the results

```bash
# from an aggregate that already exists, such as the one the journal pipeline writes
make results AGG=../deepecg-kit-journal/results/analysis/agg \
             RUNS=../deepecg-kit-journal/results/runs KIT_VERSION=0.3.0

# or straight from run directories
make results RUNS=../deepecg-kit/runs KIT_VERSION=0.3.0

make check
```

`RUNS` is where the diagnostic plots are copied from, taking the run with the lowest seed of
each pair; leave it out and the published plots stay as they are. When aggregating from run
directories, `deepecg aggregate` is called with `--on-duplicate error`, because the library
otherwise resolves a duplicated run by file time, and file times do not survive a copy.

## Adding an architecture

Register it in DeepECG-Kit and run `make registry`. It appears on the page at once, under the
registry's own name and description. An entry under `models` in `catalogue.json` gives it a
family, a summary and a reference.

`make check` fails when `catalogue.json` describes an architecture that is not registered, when
a result names an unknown architecture, task or metric, when a task's input shape has no
parameter count, or when a plot is listed but missing.

## Publishing

A push to `main` runs the tests and, if they pass, publishes `site/` to GitHub Pages
(`.github/workflows/pages.yml`; the repository's Pages source must be set to "GitHub Actions").

`archive/field-survey/` holds the literature survey the site used to show. Nothing reads it.

## Licence

Apache-2.0, matching DeepECG-Kit.
