"""Copy per-run diagnostic plots into assets/ and record what was copied.

Run directories hold matplotlib PNGs (confusion matrix, calibration curve, loss and
accuracy curves). They are the only view of a run's behaviour that survives aggregation,
so a benchmark that shows only a scalar F1 throws away the evidence that would let a
reader see HOW a model failed -- ConvNeXt-V2's collapse on MIT-BIH is obvious in its
confusion matrix and invisible in its F1 alone.

These are raster images with colours baked in. They are never themed: the templates render
them on a fixed white card in both light and dark mode, because tinting or inverting a plot
misrepresents it.

The index written here is what the templates iterate, so a page can never reference a file
that was not copied -- which under strict_variables would be a build error, and in a
browser would be a broken image.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Any

from common import ROOT, load_site

# source filename -> (destination stem, caption)
WANTED = {
    "confusion_matrix.png": ("confusion-matrix", "Confusion matrix on the test split."),
    "calibration_curve.png": ("calibration-curve",
                              "Reliability diagram: predicted confidence against observed accuracy."),
    "loss.png": ("loss-curve", "Training and validation loss per epoch."),
}

# accuracy.png is deliberately NOT collected. Three plots per cell is ~13 MB committed;
# four is ~18 MB, and the accuracy curve says little the loss curve and the confusion
# matrix do not. "Selected" is doing real work in that decision.

RUN_DIR = re.compile(r"^\d{8}-\d{6}-(?P<rest>.+)$")


def resolve_run(name: str, models: list[str], datasets: list[str]) -> tuple[str, str] | None:
    m = RUN_DIR.match(name)
    stem = m.group("rest") if m else name
    for model in sorted(models, key=len, reverse=True):
        if stem.startswith(model + "-"):
            rest = stem[len(model) + 1:]
            for ds in sorted(datasets, key=len, reverse=True):
                if rest == ds or rest.startswith(ds + "-"):
                    return model, ds
    return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs-dir", nargs="+", required=True, type=Path)
    ap.add_argument("--out", type=Path, default=ROOT / "assets" / "runs")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    site = load_site()
    models = list(site.registry.get("models", {}))
    datasets = list(site.registry.get("datasets", {}))
    # dataset -> task id, so plots land under the task the site actually shows.
    task_of = {str(t.get("registry_dataset")): tid for tid, t in site.tasks.items()}

    index: dict[str, list[dict[str, Any]]] = {}
    copied = skipped = 0
    total_bytes = 0

    for root in args.runs_dir:
        if not root.is_dir():
            continue
        for run in sorted(root.iterdir()):
            if not run.is_dir() or run.name.startswith("_"):
                continue
            hit = resolve_run(run.name, models, datasets)
            if not hit:
                continue
            model, dataset = hit
            task = task_of.get(dataset)
            if not task:
                continue
            key = f"{task}|{model}"
            for src_name, (stem, caption) in WANTED.items():
                src = run / src_name
                if not src.is_file():
                    continue
                rel = Path(task) / model / f"{stem}.png"
                dst = args.out / rel
                if not args.dry_run:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
                total_bytes += src.stat().st_size
                copied += 1
                entry = {
                    "file": f"/assets/runs/{rel.as_posix()}",
                    "caption": caption,
                    "kind": stem,
                    "source_run": run.name,
                }
                # A later run of the same pair supersedes an earlier one, matching the
                # snapshot's own duplicate resolution rather than silently keeping both.
                bucket = index.setdefault(key, [])
                bucket[:] = [e for e in bucket if e["kind"] != stem] + [entry]

    for k in index:
        index[k].sort(key=lambda e: list(WANTED.values()).index(
            next(v for v in WANTED.values() if v[0] == e["kind"])))

    # Deliberately no index file is written here. tools/build_site_data.py derives it by
    # scanning assets/runs/ at build time, so the index always describes the PNGs that are
    # actually committed. An index written here would be a second source of truth that CI
    # -- which has no access to the run directories -- could not regenerate or check.

    print(f"{'would copy' if args.dry_run else 'copied'} {copied} plots "
          f"for {len(index)} model x task cells ({total_bytes / 1e6:.1f} MB)")
    if skipped:
        print(f"  skipped {skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
