"""Export deepecgkit's model and dataset registries to site/data/registry.json.

This is the ONLY thing in the repo that imports deepecgkit (and torch), and it runs only
when someone asks for it with `make registry` -- never on the deploy path. The page reads
the committed JSON.

The output is the sole source of truth for every machine fact about a model: class,
module, description, display name, input-length bounds, parameter counts and feature
dimensions. site/data/catalogue.json owns prose and nothing else, so the two can only
disagree by failing to join -- which tools/tests/test_data.py detects -- rather than by
disagreeing on a value, which nothing can detect.

Probe shapes are read from the tasks in catalogue.json rather than hardcoded, so the
shapes we report parameter counts for cannot drift from the tasks actually benchmarked.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

# The table's "Parameters" column needs one shape common to every model so the numbers
# are comparable down the column. 12x5 is PTB-XL, the largest input.
CANONICAL_PROBE = (12, 5)


def _probe_key(channels: int, outputs: int) -> str:
    return f"{channels}x{outputs}"


def read_task_probes(catalogue: Path) -> dict[str, tuple[int, int]]:
    """Collect the distinct input shapes declared by the catalogue's tasks."""
    probes: dict[str, tuple[int, int]] = {
        _probe_key(*CANONICAL_PROBE): CANONICAL_PROBE,
    }
    for task in json.loads(catalogue.read_text(encoding="utf-8"))["tasks"]:
        channels, outputs = task.get("input_channels"), task.get("output_size")
        if isinstance(channels, int) and isinstance(outputs, int):
            probes[_probe_key(channels, outputs)] = (channels, outputs)
    return probes


def probe_model(name: str, entry: dict[str, Any], channels: int, outputs: int) -> dict[str, Any]:
    """Instantiate one model at one input shape and measure it.

    A model that cannot be built at a given shape reports status "failed" with the
    reason. It never reports a missing number: "not probed" is a fact, a blank is not.
    """
    from deepecgkit.models.factory import build_model

    try:
        model = build_model(name, input_channels=channels, output_size=outputs)
    except Exception as exc:  # noqa: BLE001 - any construction failure is a probe result
        return {"status": "failed", "params_total": None, "params_trainable": None,
                "feature_dim": None, "reason": f"{type(exc).__name__}: {exc}"[:300]}

    try:
        total = sum(p.numel() for p in model.parameters())
        trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
        feature_dim = getattr(model, "feature_dim", None)
        return {
            "status": "ok",
            "params_total": int(total),
            "params_trainable": int(trainable),
            "feature_dim": int(feature_dim) if isinstance(feature_dim, int) else None,
            "reason": None,
        }
    except Exception as exc:  # noqa: BLE001
        return {"status": "failed", "params_total": None, "params_trainable": None,
                "feature_dim": None, "reason": f"{type(exc).__name__}: {exc}"[:300]}


def git_sha(repo: Path | None) -> dict[str, Any]:
    if repo is None or not (repo / ".git").exists():
        return {"kit_git_sha": None, "kit_git_dirty": None}
    def run(*args: str) -> str | None:
        try:
            return subprocess.run(
                ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
            ).stdout.strip()
        except (subprocess.CalledProcessError, OSError):
            return None
    sha = run("rev-parse", "HEAD")
    status = run("status", "--porcelain")
    return {
        "kit_git_sha": sha[:12] if sha else None,
        "kit_git_dirty": bool(status) if status is not None else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "site" / "data" / "registry.json")
    parser.add_argument(
        "--catalogue", type=Path, default=ROOT / "site" / "data" / "catalogue.json"
    )
    parser.add_argument("--kit-repo", type=Path, default=None)
    parser.add_argument("--exported-utc", default=None, help="ISO timestamp; defaults to now")
    args = parser.parse_args(argv)

    import deepecgkit  # noqa: F401  (import for side-effect: populates the registries)
    from deepecgkit import registry as reg

    # Importing the packages registers every decorated class.
    import deepecgkit.datasets  # noqa: F401
    import deepecgkit.models  # noqa: F401

    from deepecgkit.analysis import latex

    probes = read_task_probes(args.catalogue)
    model_names = reg.get_model_names()
    dataset_names = reg.get_dataset_names()

    models: dict[str, Any] = {}
    for name in model_names:
        entry = reg._MODEL_REGISTRY[name]
        cls = entry["class"]
        record: dict[str, Any] = {
            "registry_name": name,
            "class": cls.__name__,
            "module": cls.__module__,
            "description": entry.get("description", ""),
            "head_attr": entry.get("head_attr"),
            "default_kwargs": entry.get("default_kwargs") or {},
            "min_input_length": entry.get("min_input_length"),
            "max_input_length": entry.get("max_input_length"),
            "display_name": latex.MODEL_DISPLAY_NAMES.get(name),
            "probes": {},
        }
        for key, (channels, outputs) in sorted(probes.items()):
            record["probes"][key] = probe_model(name, entry, channels, outputs)
        models[name] = record
        print(f"  probed {name}: {record['probes'][_probe_key(*CANONICAL_PROBE)]['status']}")

    datasets: dict[str, Any] = {}
    for name in dataset_names:
        entry = reg._DATASET_REGISTRY[name]
        cls = entry["class"]
        datasets[name] = {
            "registry_name": name,
            "class": cls.__name__,
            "module": cls.__module__,
            "description": entry.get("description", ""),
            "input_channels": entry.get("input_channels"),
            "num_classes": entry.get("num_classes"),
            "class_labels": list(getattr(cls, "CLASS_LABELS", []) or []),
            "binary_class_labels": list(getattr(cls, "BINARY_CLASS_LABELS", []) or []),
            "display_name": latex.DATASET_DISPLAY_NAMES.get(name),
        }

    # Vocabularies exported so the catalogue's metric list can be CHECKED against the
    # library rather than duplicating it. tools/tests/test_data.py fails if they disagree.
    from deepecgkit.analysis import aggregation

    constants = {
        "single_label_metrics": list(aggregation.SINGLE_LABEL_METRICS),
        "multi_label_metrics": list(aggregation.MULTI_LABEL_METRICS),
        "calibration_metrics": list(aggregation.CALIBRATION_METRICS),
        "lower_is_better": sorted(latex.LOWER_IS_BETTER),
        "metric_display_names": dict(latex.METRIC_DISPLAY_NAMES),
        "averaging_macro_label": aggregation.AVERAGING_MACRO_LABEL,
        "averaging_unknown": aggregation.AVERAGING_UNKNOWN,
        "legacy_seed": aggregation.LEGACY_SEED,
    }

    from datetime import datetime, timezone

    meta = {
        "kit_version": getattr(deepecgkit, "__version__", None),
        "kit_source": None,
        "exported_utc": args.exported_utc or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "python": sys.version.split()[0],
        "n_models": len(models),
        "n_datasets": len(datasets),
        "canonical_probe": _probe_key(*CANONICAL_PROBE),
        "probes": {k: {"input_channels": v[0], "output_size": v[1]} for k, v in sorted(probes.items())},
        **git_sha(args.kit_repo),
    }
    try:
        import torch

        meta["torch"] = torch.__version__
    except Exception:  # noqa: BLE001
        meta["torch"] = None

    payload = {"meta": meta, "models": models, "datasets": datasets, "constants": constants}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    print(f"\nwrote {args.out}: {len(models)} models, {len(datasets)} datasets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
