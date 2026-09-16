---
layout: default
title: Methodology
permalink: /methodology/
---

<header class="hero"><div class="wrap">
<h1>Methodology</h1>
</div></header>

<div class="wrap-narrow prose" style="padding:32px 24px 48px">

## Why this page exists first

The journal companion to DeepECG-Kit argues that single-run leaderboards are unreliable: that
replicate variance, convergence rate and rank instability decide whether a comparison means
anything, and that *"no cell may be left blank; each is either a measured value or an explicit
status."* A benchmark site that ignored that would contradict its own paper. So the integrity
rules were written before the templates, and most of them are enforced by `tools/validate.py`
rather than by good intentions.

## The five rules

1. **One table per task.** Metrics from different tasks are not commensurable. There is no
   site-wide ranking and no "best architecture" string anywhere in any template.
2. **No blank cells.** Every model&times;task pair carries a measured value or a stated reason.
   `tools/build_site_data.py` fails the build if any cell lacks a status.
3. **Nothing is bolded as a winner.** Marking a best mean is a pairwise claim that per-model
   intervals cannot support. `deepecgkit.analysis.latex.results_table()` bolds nothing for exactly
   this reason, and the site keeps the rule.
4. **Non-convergent runs are shown at their measured values.** The conference paper omitted models
   that failed to converge; this site does not. ConvNeXt-V2 on MIT-BIH AFDB scores F1 **0.000** and
   that number is on the page, flagged.
5. **Provenance travels with every number.** Snapshot id, library version and commit, replicate
   count and age appear beside every table, not in a footer.

## What a replicate is

A *replicate* is one training run differing only in random seed. The journal protocol specifies
grouped five-fold cross-validation over recordings for the Holter tasks (MIT-BIH AFDB and LTAFDB),
which is a different and stronger notion: it varies *which recordings* are held out, so its
dispersion includes between-subject variation.

The library cannot currently record a fold id &mdash; `run_metadata.json` has no field for one, and
the only replicate key `deepecgkit.analysis.aggregation` understands is a seed. Each task therefore
declares `replicate_kind`, and any task whose committed replicates are seeds standing in for folds
carries a note saying so. Read seed dispersion as training stochasticity only.

## Intervals

Where a dispersion is shown it is a **Student-t interval over replicates**, computed by
`deepecgkit.analysis.statistics`. It is not a bootstrap confidence interval over test recordings,
which is what the journal protocol asks for and what would capture sampling variation in the test
set. Column headers say "t-interval over N replicates" and never "CI", and a bootstrap column
reads `not measured` rather than being absent.

`MIN_SEEDS_FOR_INTERVAL` is 3 and `MIN_SEEDS_FOR_CLAIM` is 5 in the library. Below three
replicates no dispersion is estimable, so the standard-deviation column renders an em dash rather
than `0.000` &mdash; a zero would imply a precision that does not exist.

## Averaging modes

Precision, recall and F1 are **not comparable across averaging modes**.
`deepecgkit.evaluation.metrics.resolve_average()` returns `binary` whenever the realised test split
holds two or fewer classes and `macro` otherwise, and it records which it applied.

Two gates guard this. `reconcile_averaging()` in the library drops runs whose mode disagrees with
their group &mdash; but it groups by `(dataset, model)`, so it cannot see a `binary` F1 sitting
beside a `macro` F1 in the same *column*. `tools/validate.py` adds that check per
`(dataset, metric)`, and separately compares each task's declared `expected_averaging` against what
the snapshot actually observed, because a split changing shape silently changes what the number
means.

Legacy runs predating the `average` column report `unknown`. That is *unrecorded*, not
*conflicting*, and the site labels it as such rather than guessing.

## Convergence

The site never computes convergence. Re-implementing the journal's criterion here would ship a
weaker test under the paper's name and could contradict the library's own verdict on an adjacent
page. Until `classification_metrics.csv` carries a `converged` column, every measured cell is
marked **convergence not reported**.

One thing the site does state, because it is a direct reading of the committed numbers rather than
a verdict: when a cell's precision and recall are both exactly zero, it is flagged **zero predicted
positives**. That is arithmetic, not a criterion.

## Provenance is auditable, not verifiable

Each snapshot manifest records the library version, git commit and dirty flag. These are
**self-reported by the tool that built the snapshot**, not recorded when the model was trained: the
current `run_metadata.json` schema has no version field. Nothing in the committed artefacts proves
the CSVs came from the commit the manifest names.

The fix is upstream and small &mdash; write `deepecgkit_version` and `git_sha` into
`run_metadata.json` at train time &mdash; and until it lands, treat provenance here as an audit
trail a human can follow, not a cryptographic guarantee. Raw run directories stay on the machine
that produced them; only the aggregated CSVs are published.

## Consistency is not correctness

Every gate in this repo checks that the site agrees with its inputs. **None of them checks that the
inputs are right.** A leaking split, a mislabelled class or a truncated signal produces a wrong
number that will pass every check and be rendered inside a perfect provenance record.

`_data/known_defects.yml` is the only mechanism that says so. It joins on
`(kit_version, dataset)` and renders a warning chip on affected cells and a banner on the task page.
It is a human-maintained list, and it is only as complete as the defects someone has noticed.

## The field survey

The catalogue includes architectures that are **not** implemented in DeepECG-Kit, so the table is
a view of the field rather than an advertisement for one library. Two rules keep that honest:

- Survey rows carry only literature-reported facts. Nothing about them is measured by this site,
  and their parameter counts are marked with a dagger when the authors report one. The build
  refuses a survey entry carrying a measured-fact key.
- A survey architecture **may** hold a result cell, but only an amber one sourced from
  `_data/reported.yml`, and only on a task some paper actually cites it for — the citation creates
  the cell, rather than the model × task grid. Two consequences keep this honest. The cell takes
  whichever metric the paper reports, because most ECG papers publish macro-AUC where this site
  ranks on macro-F1, and a survey row carrying an empty F1 would say nothing. And survey cells are
  excluded from the coverage denominator: adding a citation must never move a percentage that
  describes what this site *measured*, nor make that denominator grow every time someone reads a
  paper.
- A survey entry whose name matches a registered model fails the build. When an architecture gets
  implemented, its survey entry must be deleted and replaced by a catalogue page — a model must
  never appear twice with two sets of facts.

The survey describes the field, not only the part of it this site benchmarks, so it includes work
that could never hold a result cell: delineation and R-peak detection networks, and generative,
denoising and ECG-image models. `family` names the architectural trunk — convolutional, recurrent,
hybrid, attention, state-space, foundation — except for `segmentation` and `generative`, which name
what the model *outputs*, because filing a U-Net delineator under "convolutional" would describe its
layers and misdescribe the model.

Identifiers follow the same policy as everywhere else: a DOI or arXiv id appears only when
verified, and an absent identifier is preferred to a plausible one. Every identifier in the survey
was resolved against the Crossref or arXiv API and the returned title matched against the recorded
one; entries that failed were dropped rather than guessed. This matters more than it sounds: a
guessed DOI almost always resolves to a real but unrelated paper, so it survives every automated
check and reads as a citation.

## Images

Diagnostic plots from run directories (confusion matrices, calibration curves, training curves) are
matplotlib PNGs with colours baked in. They are **never themed**: they render on a fixed white card
with a border in both light and dark mode, because tinting or inverting a plot misrepresents it.
Charts generated by this site are inline SVG and do follow the theme.

## Reproducing a snapshot

```bash
# 1. Train, in the library repo
python scripts/run_experiments.py

# 2. Snapshot, in this repo
python tools/make_snapshot.py --id <id> --label "<what these runs are>" \
  --status preliminary --kit-repo ../deepecg-kit --runs-dir <path-to-runs>

# 3. Point the site at it, then verify
#    edit _data/snapshots.yml: current: <id>
make validate && make data && make build
```

`make_snapshot.py` always tries `--on-duplicate error` first. `deepecgkit` resolves duplicate
`(dataset, model, seed)` keys by filesystem mtime, and mtime does not survive `cp`, `clone` or
`rsync` &mdash; so two people running the identical documented command could otherwise publish
different winners. Duplicates must be seen and accepted explicitly.

</div>
