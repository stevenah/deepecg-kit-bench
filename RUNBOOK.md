# Runbook: producing a seeded snapshot

How to go from nothing measured to a published snapshot. Written after preparing the full
grid, so the traps below are ones actually hit rather than imagined.

Everything in step 0 and 1 happens in the **library** repo (`../deepecg-kit`); step 4 onward
happens **here**.

## What this produces

100 pairings (20 architectures × 5 datasets) × 5 seeds = **500 training runs**, replacing the
current `2026-cbms-preliminary` snapshot, which carries `include_legacy: true` and
`replicate_ids: [-1]` — one seedless run per pair. That is why the grid is the whole 100 and
not just the 76 empty cells: a snapshot is aggregated from run directories, the old runs are
no longer on disk, and re-running the covered pairs is what turns the next snapshot from
*preliminary* into one that can be declared **current**.

`afmodel` is excluded, so it is 20 architectures and not 21. `AFModel(recording_length=30)`
needs ≥ 7971 samples per lead; these datasets emit 3000 (300 Hz × 10 s) or 5000 (PTB-XL,
500 Hz × 10 s). All five of its pairings fail at build time. This is structural, not an
oversight — see the comment at the top of `experiments.yaml`.

## 0. Data — about 5.6 GB, none of it present yet

Nothing is downloaded. `~/.deepecgkit/datasets/` holds two directories, and both are traps:

| dataset | on disk | real size | note |
|---|---|---|---|
| `challenge-2017` | 45 MB zip | **1.48 GB** | a failed partial download |
| `ptb-xl` | empty dir | **1.84 GB** | — |
| `afdb` | absent | 0.46 GB | — |
| `ltafdb` | absent | 1.78 GB | — |
| `unified-af` | — | — | derived from the three AF sets, no separate download |

**The partial zip matters.** `BaseDataset._data_dir_is_empty()` is `not any(dir.iterdir())`, so
a directory holding a truncated 45 MB zip counts as *not empty* and `download=True` will not
re-fetch it. Force that one:

```bash
cd ../deepecg-kit
.venv/bin/deepecg train --model resnet --dataset af-classification --epochs 1 --force-download
```

The others download on first use. To fetch them without training a real model, run one
1-epoch job per dataset; that also proves the loader and the split work before you commit to
500 runs:

```bash
for d in ptbxl mitbih-afdb ltafdb unified-af; do
  .venv/bin/deepecg train --model simple-cnn --dataset "$d" --epochs 1 || break
done
```

## 1. Preflight — 23 seconds, no data needed

```bash
cd ../deepecg-kit
.venv/bin/python scripts/preflight_experiments.py
```

Builds every pairing at the sequence length its dataset really emits and pushes one batch
through. It is a shape-and-arity check only: it says nothing about whether a run converges.
It exists because a sweep that dies on run 340 for a reason knowable in 23 seconds has wasted
a day. Exit 1 on any failure, so it can gate the sweep:

```bash
.venv/bin/python scripts/preflight_experiments.py && \
  .venv/bin/python scripts/run_experiments.py --resume
```

## 2. Sanity-check the plan before committing

```bash
.venv/bin/python scripts/run_experiments.py --dry-run | head -20   # 500 commands, seeds echoed
.venv/bin/python scripts/run_experiments.py --only resnet:ptbxl    # one pairing, 5 seeds
```

`--dry-run` echoes the resolved seed list. Worth reading: YAML parses a zero-padded `042` as
octal `34`, and the echo is the cheap way to see that.

## 3. Run

```bash
.venv/bin/python scripts/run_experiments.py --resume --continue-on-error
```

- `--resume` reconciles against the run directories, not just its cache, so Ctrl-C and restart
  is cheap and will not re-train work already on disk.
- `--continue-on-error` keeps going past a failure. Without it the sweep stops at the first
  one, which is what you want on a first attempt and not what you want overnight.
- Runs land in `runs/{model}-{dataset}-seed{N}/`.
- `--limit N` attempts only the first N, leaving progress intact — good for timing one pairing
  before extrapolating to 500.

Time it on one run before trusting any estimate: 500 runs at 50 epochs each is the kind of
number that is either an afternoon or a fortnight depending entirely on the accelerator.

## 4. Snapshot, back in this repo

```bash
cd ../deepecg-kit-bench
python tools/make_snapshot.py --id 2026-09-seeded --label "5 seeds per pair, full grid" \
  --status current --kit-repo ../deepecg-kit --runs-dir ../deepecg-kit/runs
```

`--status current` is only honest once `include_legacy` is off — the validator's
`E_LEGACY_STATUS` gate refuses a snapshot that pooled seedless runs while calling itself
current, which is exactly the mistake this sweep exists to stop making.

## 5. Publish

```bash
# point the site at it
$EDITOR _data/snapshots.yml        # current: 2026-09-seeded
make check && make build
```

## Two things to decide before you start

**LTAFDB.** `_data/known_defects.yml` carries `ltafdb-memmap-truncation` (severity high:
signals read from a silently truncated memmap) capped at `kit_version_max: 0.2.0`. The
library's CHANGELOG shows this **fixed** under `[Unreleased]` — "Growing the LTAFDB cache
memmap silently kept its original capacity" — but `pyproject.toml` still says `version =
"0.2.0"`, which is what the site's defect gate joins on. So unless the library is versioned
past 0.2.0 before you snapshot, every LTAFDB cell will render a *known defect* chip even
though the code is fixed. Either bump the version, or drop LTAFDB from this sweep with
`--only` and add it later. Also: any LTAFDB cache built before the fix is still truncated —
clear `~/.deepecgkit/datasets/ltafdbdataset` first.

**Convergence.** `MAINTAINING.md` lists a convergence column in `classification_metrics.csv`
as the second-highest-value upstream change. Until it exists, every measured cell renders
*convergence not reported* and the `non_convergent` status is unreachable — so a 500-run sweep
still cannot say whether any of it converged. Worth adding upstream before the sweep rather
than after, since it costs nothing at train time and cannot be recovered afterwards.
