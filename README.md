# DeepECG-Bench

A catalogue of every architecture registered in [DeepECG-Kit](https://github.com/stevenah/deepecg-kit),
and an honest account of what has actually been measured on each one.

**https://stevenah.github.io/deepecg-kit-bench/**

The model-side counterpart to [ECGBench](https://vajira.info/ECGBench/), which catalogues ECG
*datasets*. This site catalogues *models*, and publishes benchmark results as immutable, cited
snapshots.

## The one rule

**`_models/*.md` contains no machine fact.** No parameter count, no feature dimension, no
input-length bound, no metric. Those live in generated `_data/registry.json` and in
`results/snapshots/`, joined at render time on `registry_name`.

Drift then degrades into a **join failure**, which the validator detects, rather than a **value
mismatch**, which nothing detects. `tools/validate.py` enforces it: a hand-written `params_total:`
in a model page fails the build and names the file that owns the value.

## Layout

| Path | What it is | Written by |
|---|---|---|
| `_models/*.md` | One page per architecture. Prose only. | Hand |
| `_tasks/*.md` | One page per benchmark task. Protocol and caveats. | Hand |
| `_data/registry.json` | Every machine fact about every model. | `tools/export_registry.py` (bot PR) |
| `_data/field.yml` | The field survey: architectures not implemented here, literature facts only. | Hand |
| `_data/{families,metrics,statuses,known_defects}.yml` | Vocabularies. | Hand |
| `results/snapshots/<id>/` | Immutable published results + manifest + checksums. | `tools/make_snapshot.py` |
| `assets/runs/<task>/<model>/` | Committed diagnostic PNGs. | `tools/collect_plots.py` |
| `_data/generated/`, `_includes/charts/generated/` | Build products. Gitignored. | `tools/build_site_data.py` |

## Commands

```bash
make validate     # every integrity gate; exits non-zero on any failure
make data         # generated JSON + inline SVG charts
make build        # jekyll build into _site/
make serve        # local preview at http://localhost:4000/deepecg-kit-bench/
make check        # validate + data + tool tests -- what CI runs
make identifiers  # resolve every DOI/arXiv id and check it names the paper we claim
make registry     # re-export _data/registry.json (needs torch)
```

`make identifiers` is the only target that touches the network, which is why it is not part of
`make check`: a build that fails because Crossref is having a bad afternoon teaches people to
ignore the build. Run it when you add citations. It exists because it is the one thing the other
gates cannot do — a wrong DOI still resolves, usually to a real but unrelated paper, so it
survives every syntactic check and reads to a human as a citation. Narrow it with
`ARGS=--reported`, `--field` or `--models`.

## Adding a paper's results

`_data/reported.yml` is one block per paper: write the citation and the protocol note once, and
hang every value that paper reports off it.

```yaml
- source:
    paper_title: "..."
    doi: "..."                     # or "arXiv:2410.08559"
  protocol_note: >-
    What split, what averaging, and whether this is the architecture's own authors or a
    third party's re-implementation of it.
  values:
    - {model: st-mem, task: ptbxl-multilabel, metric: f1, value: 0.662, n: null}
```

`model` is a `registry_name` or a `_data/field.yml` slug — a survey architecture may hold a cell,
but only an amber one, and only on a task some paper actually cites it for. Then
`make identifiers ARGS=--reported && make check`.

## Publishing a new set of results

```bash
# 1. Train, in the library repo
python scripts/run_experiments.py

# 2. Snapshot, here
python tools/make_snapshot.py --id 2026-06-seeded --label "5 seeds per pair" \
  --status current --kit-repo ../deepecg-kit --runs-dir ../deepecg-kit/runs

# 3. Optional: copy diagnostic plots
python tools/collect_plots.py --runs-dir ../deepecg-kit/runs

# 4. Point the site at it, verify, open a PR
#    edit _data/snapshots.yml -> current: 2026-06-seeded
make check && make build
```

`make_snapshot.py` always tries `--on-duplicate error` first, because deepecgkit resolves
duplicate `(dataset, model, seed)` keys by filesystem mtime and mtime does not survive `cp`,
`clone` or `rsync`. Two people running the same documented command could otherwise publish
different numbers.

## Notes on the build

- **Liquid runs with `strict_variables`.** A missing key is a build error, including on a plain
  hash. Generated records are therefore *total*: every row carries every key, empty where it has
  no value. `tools/validate.py` checks the front-matter key set so a contributor gets a message
  naming the file rather than a Liquid line number.
- **`id` is reserved.** Jekyll's `Document#id` returns the document URL, so task and snapshot
  pages use `task_id` / `snapshot_id`.
- **No plugins.** `jekyll-sitemap`'s template is not strict-safe; `sitemap.xml` here is ours.
  Staying plugin-free also keeps the site buildable by GitHub Pages' safe-mode Jekyll.
- **No charting library.** Charts are SVG generated from the same validated JSON that fills the
  tables, inlined so they follow the theme with no JavaScript.
- **Torch is never on the deploy path.** Only `tools/export_registry.py` imports the library, and
  it runs in the refresh-registry bot job.

See [MAINTAINING.md](MAINTAINING.md) for the upkeep contract.

## Licence

Apache-2.0, matching DeepECG-Kit.
