"""Turn a `deepecg aggregate` output directory into site/data/results.json.

    python tools/build_results.py AGG_DIR [--runs-dir DIR] [--kit-version X.Y.Z]

AGG_DIR holds seed_metrics_long.csv and seed_runs_long.csv, exactly as
`deepecg aggregate --output-dir AGG_DIR` writes them. Nothing is recomputed here: every
mean, deviation and interval on the page is the library's own number.

With --runs-dir, each pair's diagnostic plots are copied into site/plots/ from the run of
its lowest seed. The run is named by seed_runs_long.csv, so only runs that contributed
numbers are used; it is looked up by directory name under --runs-dir because the paths in
that file are absolute on the machine that trained. Without --runs-dir the plots already
in site/plots/ are left alone and listed as they are.

Stdlib only, so it runs anywhere the CSVs are.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

SCHEMA = 1

# deepecgkit.analysis.aggregation: the seed given to a run whose seed cannot be
# determined, and the averaging mode of a run that recorded none.
LEGACY_SEED = -1
AVERAGING_UNKNOWN = "unknown"

# Run-directory file -> the name it is published under. accuracy.png is deliberately not
# collected: three plots per pair are already about 0.5 MB, and the accuracy curve says
# little that the loss curve and the confusion matrix do not.
PLOTS = {
    "confusion_matrix.png": "confusion-matrix",
    "calibration_curve.png": "calibration-curve",
    "loss.png": "loss-curve",
}


def number(text: str | None) -> float | None:
    """A CSV cell as a finite float; empty, NaN and infinite all become None."""
    if text is None or text == "":
        return None
    value = float(text)
    return value if math.isfinite(value) else None


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_site(site: Path) -> tuple[dict[str, str], list[str], set[str]]:
    """The joins the results must satisfy: dataset -> task, metric order, model names."""
    catalogue = json.loads((site / "data" / "catalogue.json").read_text(encoding="utf-8"))
    registry = json.loads((site / "data" / "registry.json").read_text(encoding="utf-8"))
    task_of: dict[str, str] = {}
    for task in catalogue["tasks"]:
        if task["dataset"] in task_of:
            raise SystemExit(
                f"dataset '{task['dataset']}' belongs to two tasks ({task_of[task['dataset']]}, "
                f"{task['id']}); the aggregate records only the dataset, so its rows could not "
                f"be attributed."
            )
        task_of[task["dataset"]] = task["id"]
    return task_of, [m["id"] for m in catalogue["metrics"]], set(registry["models"])


def build_rows(
    metric_rows: list[dict[str, str]],
    run_rows: list[dict[str, str]],
    task_of: dict[str, str],
    metric_order: list[str],
    models: set[str],
) -> tuple[list[dict[str, Any]], list[str]]:
    """One record per (model, task), plus every reason the input cannot be published."""
    problems: list[str] = []
    for kind, known, hint in (
        ("dataset", set(task_of), "no task in catalogue.json uses it"),
        ("model", models, "not in registry.json; run `make registry` or check the name"),
        ("metric", set(metric_order), "add it to the metrics in catalogue.json"),
    ):
        for name in sorted({r[kind] for r in metric_rows} - known):
            problems.append(f"unknown {kind} '{name}': {hint}")
    if problems:
        return [], problems

    # (model, dataset, metric) -> per-seed values, and (model, dataset) -> seed -> run_dir.
    values: dict[tuple[str, str, str], list[tuple[int, float | None]]] = {}
    runs: dict[tuple[str, str], dict[int, str]] = {}
    for r in run_rows:
        seed = int(float(r["seed"]))
        values.setdefault((r["model"], r["dataset"], r["metric"]), []).append(
            (seed, number(r["value"]))
        )
        runs.setdefault((r["model"], r["dataset"]), {})[seed] = r["run_dir"]

    rows: dict[tuple[str, str], dict[str, Any]] = {}
    for r in metric_rows:
        key = (r["model"], r["dataset"])
        row = rows.setdefault(key, {
            "model": r["model"],
            "task": task_of[r["dataset"]],
            "averaging": None,
            "runs": 0,
            "seeds": sorted(s for s in runs.get(key, {}) if s != LEGACY_SEED),
            "metrics": {},
            "run_dirs": runs.get(key, {}),
        })
        if r["metric"] in row["metrics"]:
            problems.append(f"{r['model']} on {r['dataset']} lists {r['metric']} twice")
        if r.get("averaging") and r["averaging"] != AVERAGING_UNKNOWN:
            row["averaging"] = r["averaging"]
        row["runs"] = max(row["runs"], int(float(r.get("n_runs") or r["n"] or 0)))
        n = int(float(r["n"] or 0))
        if n == 0:
            # No run could compute it, such as per-label scaling on a softmax task.
            continue
        row["metrics"][r["metric"]] = {
            "n": n,
            "mean": number(r["mean"]),
            "std": number(r["std"]),
            "lo": number(r["lower_ci"]),
            "hi": number(r["upper_ci"]),
            "values": [
                v for _, v in sorted(values.get((*key, r["metric"]), []), key=lambda sv: sv[0])
            ],
        }

    task_order = list(task_of.values())
    ordered = sorted(rows.values(), key=lambda x: (task_order.index(x["task"]), x["model"]))
    for row in ordered:
        row["metrics"] = {m: row["metrics"][m] for m in metric_order if m in row["metrics"]}
    return ordered, problems


def copy_plots(row: dict[str, Any], runs_dir: Path, plots: Path) -> None:
    """Copy the plots of this pair's lowest-seed run, replacing any already published."""
    run_dirs: dict[int, str] = row["run_dirs"]
    if not run_dirs:
        return
    seed = min(run_dirs)
    source = runs_dir / Path(run_dirs[seed]).name
    if not source.is_dir():
        print(f"  no run directory {source.name} under {runs_dir}; plots unchanged for "
              f"{row['model']} on {row['task']}", file=sys.stderr)
        return
    target = plots / row["task"] / row["model"]
    if target.exists():
        shutil.rmtree(target)
    for filename, kind in PLOTS.items():
        if (source / filename).is_file():
            target.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / filename, target / f"{kind}.png")
    row["plot_seed"] = seed if seed != LEGACY_SEED else None


def list_plots(row: dict[str, Any], plots: Path) -> list[str]:
    """The plot kinds actually on disk for this pair, in display order."""
    folder = plots / row["task"] / row["model"]
    present = {p.stem for p in folder.glob("*.png")} if folder.is_dir() else set()
    return [kind for kind in PLOTS.values() if kind in present]


def dump(payload: dict[str, Any]) -> str:
    """JSON with one metric per line, so a refresh reads as a diff of numbers."""
    def compact(value: Any) -> str:
        return json.dumps(value, allow_nan=False, ensure_ascii=False)

    head = [f' "{k}": {compact(v)},' for k, v in payload.items() if k != "rows"]
    rows = []
    for row in payload["rows"]:
        fields = [f'"{k}": {compact(v)}' for k, v in row.items() if k != "metrics"]
        metrics = ",\n".join(f'    "{m}": {compact(v)}' for m, v in row["metrics"].items())
        rows.append("  {" + ", ".join(fields) + ',\n   "metrics": {\n' + metrics + "\n   }}")
    return "{\n" + "\n".join(head) + '\n "rows": [\n' + ",\n".join(rows) + "\n ]\n}\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("agg_dir", type=Path, help="output directory of `deepecg aggregate`")
    parser.add_argument("--runs-dir", type=Path, default=None, help="copy plots from these runs")
    parser.add_argument("--kit-version", default=None, help="deepecgkit version that trained")
    parser.add_argument("--generated", default=None, help="ISO timestamp; defaults to now")
    parser.add_argument("--confidence-level", type=float, default=0.95,
                        help="coverage passed to `deepecg aggregate` (its default: 0.95)")
    parser.add_argument("--site", type=Path, default=ROOT / "site", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    for name in ("seed_metrics_long.csv", "seed_runs_long.csv"):
        if not (args.agg_dir / name).is_file():
            print(f"{args.agg_dir} has no {name}; is it a `deepecg aggregate` output directory?",
                  file=sys.stderr)
            return 1
    metric_rows = read_csv(args.agg_dir / "seed_metrics_long.csv")
    run_rows = read_csv(args.agg_dir / "seed_runs_long.csv")

    task_of, metric_order, models = load_site(args.site)
    rows, problems = build_rows(metric_rows, run_rows, task_of, metric_order, models)
    if problems:
        print(f"{len(problems)} problem(s); results.json not written:", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        return 1

    plots = args.site / "plots"
    for row in rows:
        row["plot_seed"] = None
        if args.runs_dir is not None:
            copy_plots(row, args.runs_dir, plots)
        del row["run_dirs"]
        row["plots"] = list_plots(row, plots)

    payload = {
        "schema": SCHEMA,
        "generated": args.generated
        or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "kit_version": args.kit_version,
        "confidence_level": args.confidence_level,
        "n_runs": len({r["run_dir"] for r in run_rows}),
        "rows": rows,
    }
    out = args.site / "data" / "results.json"
    out.write_text(dump(payload), encoding="utf-8")

    published = {(r["task"], r["model"]) for r in rows}
    orphans = sorted(
        str(p.relative_to(args.site)) for p in plots.glob("*/*")
        if p.is_dir() and (p.parent.name, p.name) not in published
    )
    print(f"wrote {out}: {len(rows)} pairs from {payload['n_runs']} runs, "
          f"{sum(len(r['plots']) for r in rows)} plots")
    for orphan in orphans:
        print(f"  {orphan} has plots but no result; delete it", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
