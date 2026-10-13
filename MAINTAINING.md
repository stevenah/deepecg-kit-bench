# Maintaining this site

## Who and how often

One maintainer. There is no cadence obligation: the site is designed to stay *honest* while
unattended rather than to require attention.

| Trigger | Action | Cost |
|---|---|---|
| An architecture added or removed upstream | Merge the registry-refresh PR, write `_models/<name>.md` | ~15 min |
| A new set of runs finishes | `make_snapshot.py`, flip `_data/snapshots.yml`, PR | ~10 min |
| A defect discovered in published numbers | Add an entry to `_data/known_defects.yml` | ~5 min |
| A paper worth citing results from | Add one block to `_data/reported.yml`, then `make identifiers ARGS=--reported` | ~5 min |
| A notable architecture nobody has catalogued | Add one entry to `_data/field.yml`, then `make identifiers ARGS=--field` | ~5 min |
| Nothing | Nothing | The site ages visibly on its own |

## What happens if nobody touches it

By design, degradation is *visible rather than silent*:

- `assets/js/age.js` computes the snapshot's age **in the reader's browser** from an embedded
  timestamp. After six months every results page shows an amber banner; after a year, red. This
  works even though GitHub disables `schedule:` triggers after 60 days of repository inactivity —
  which is precisely when a staleness warning matters most.
- The evidence banner recomputes coverage from the data on every build, so it can never
  overstate what has been measured.
- `manifest.status` renders on every table sourced from that snapshot. A `preliminary` snapshot
  keeps saying so indefinitely.

The failure mode this avoids: a site that looks maintained, showing numbers from three library
versions ago, with nothing on the page to say so.

## What will rot

Honest list.

- **`_data/known_defects.yml`** is hand-maintained and only as complete as the defects someone
  noticed. Nothing detects an unknown defect.
- **`family` assignments** are editorial and unverifiable. If the library ever grows a `FAMILY`
  class attribute, delete the field here and read it from the registry instead.
- **Model page prose.** Most pages launched as valid stubs. A stub renders correctly and is
  schema-valid, so there is no build pressure to finish them — only the reader's experience.
- **Citations.** `make identifiers` resolves every DOI and arXiv id and checks the registered title
  against the one we wrote down, so a *wrong* identifier is now caught rather than merely a missing
  one. It is not in `make check` because it needs the network — so it only protects you if someone
  runs it. Four model pages carry no DOI: `afmodel`, `dualnet`, `simple-cnn` and `spectrogram-cnn`
  are in-house designs with no origin paper, so by nature.
- **`_data/reported.yml` precedence.** Where two papers report the same architecture on the same
  task, only one can fill the cell, and which one is a judgement recorded in a comment rather than
  enforced by a gate. If a better-documented source appears, nothing will tell you the old choice
  is now the worse one.
- **Protocol notes.** They are prose, and nothing checks that a note still describes the value
  beside it. The block shape makes drift less likely — one note per paper, not one per row — but
  a note edited without re-reading the paper is still a silent error.

## Upstream changes that would retire code here

Ordered by value per line changed.

1. **`run_metadata.json` schema v2** — write `deepecgkit_version`, `git_sha` and `git_dirty` at
   *train* time. This is the only change that converts the manifest's provenance claim from an
   assertion into a derivation. Smallest diff, largest gain.
2. **A convergence column** in `classification_metrics.csv`. The site refuses to compute
   convergence itself, so until this exists every measured cell reads *convergence not reported*
   and the `non_convergent` status is unreachable.
3. **`deepecg export-registry --format json`** — `tools/export_registry.py` collapses to a shim,
   and probe kwargs live beside the models they describe.
4. **`aggregate` writing its diagnostics to a file** instead of printing them. Ten lines upstream
   retires `make_snapshot.py`'s transcript parsing.
5. **Retire the family table in `docs/user-guide/model-zoo.md`** in favour of a link here.
   Until then this site *adds* a taxonomy rather than replacing one.

## Local development

System Ruby on macOS is 2.6, so the `Gemfile` pins `jekyll-sass-converter ~> 2.2` (3.x needs Ruby
≥ 3.1). The site uses plain CSS with custom properties, so the converter is never invoked — the
pin only keeps bundler's resolution reachable. CI uses Ruby 3.3 against the same lock file.

```bash
export GEM_HOME="$PWD/vendor/gems" PATH="$PWD/vendor/gems/bin:$PATH"
bundle install
make check && make build
```
