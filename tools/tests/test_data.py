"""The three data files join, and the page's references resolve.

The page draws whatever these files say, so a broken join would show up as an empty cell
or a missing row rather than as an error. These tests are where it shows up instead.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SITE = REPO / "site"


def load(name: str) -> dict:
    return json.loads((SITE / "data" / f"{name}.json").read_text(encoding="utf-8"))


CATALOGUE = load("catalogue")
REGISTRY = load("registry")
RESULTS = load("results")

FAMILIES = {f["id"] for f in CATALOGUE["families"]}
TASKS = {t["id"]: t for t in CATALOGUE["tasks"]}
METRICS = {m["id"]: m for m in CATALOGUE["metrics"]}
PROSE = {m["name"]: m for m in CATALOGUE["models"]}
MODELS = REGISTRY["models"]


def test_every_catalogue_entry_is_a_registered_architecture() -> None:
    """Prose for a name the library does not register is a typo or a removed model.

    The reverse is allowed: a registered architecture without prose still gets a row,
    drawn from the registry's own name and description.
    """
    orphans = sorted(set(PROSE) - set(MODELS))
    assert not orphans, f"catalogue.json describes unregistered architectures: {orphans}"
    assert len(PROSE) == len(CATALOGUE["models"]), "an architecture is described twice"


def test_catalogue_references_resolve() -> None:
    for name, model in PROSE.items():
        assert model["family"] in FAMILIES, f"{name}: unknown family {model['family']!r}"
        adapted = model.get("adapted_from")
        assert adapted is None or adapted in MODELS, f"{name}: adapted_from {adapted!r} is not registered"


def test_each_dataset_belongs_to_one_task() -> None:
    """The aggregate records only the dataset, so two tasks on one dataset cannot be told apart."""
    datasets = [t["dataset"] for t in CATALOGUE["tasks"]]
    assert len(datasets) == len(set(datasets)), f"a dataset is used by two tasks: {datasets}"
    unknown = sorted(set(datasets) - set(REGISTRY["datasets"]))
    assert not unknown, f"tasks use datasets the library does not register: {unknown}"


def test_every_task_shape_was_probed() -> None:
    """Parameter counts are shown per task shape; re-run `make registry` after changing one."""
    probed = REGISTRY["meta"]["probes"]
    for task in CATALOGUE["tasks"]:
        key = f"{task['input_channels']}x{task['output_size']}"
        assert key in probed, f"{task['id']}: shape {key} is not in registry.json; run `make registry`"
        missing = sorted(name for name, m in MODELS.items() if key not in m["probes"])
        assert not missing, f"{task['id']}: no {key} parameter count for {missing}"


def test_metrics_agree_with_the_library() -> None:
    """Direction decides sorting and highlighting, so it must be the library's, not ours."""
    constants = REGISTRY["constants"]
    vocabulary = set(constants["single_label_metrics"]) | set(constants["multi_label_metrics"])
    lower = set(constants["lower_is_better"])
    for name, metric in METRICS.items():
        assert name in vocabulary, f"{name} is not a metric deepecgkit computes"
        assert metric["better"] in ("higher", "lower", None), f"{name}: bad direction"
        if metric["better"] is not None:
            assert (metric["better"] == "lower") == (name in lower), f"{name}: direction disagrees with deepecgkit"
    assert len(METRICS) == len(CATALOGUE["metrics"]), "a metric is listed twice"


def test_results_join() -> None:
    seen: set[tuple[str, str]] = set()
    for row in RESULTS["rows"]:
        pair = (row["model"], row["task"])
        assert row["model"] in MODELS, f"results name an unregistered architecture: {row['model']}"
        assert row["task"] in TASKS, f"results name an unknown task: {row['task']}"
        assert pair not in seen, f"{pair} appears twice"
        seen.add(pair)
        assert row["metrics"], f"{pair} has no metrics"
        for name, value in row["metrics"].items():
            assert name in METRICS, f"{pair}: metric {name!r} is not in catalogue.json"
            assert value["n"] >= 1, f"{pair} {name}: n must be at least 1"
            numbers = [value["mean"], value["std"], value["lo"], value["hi"], *value["values"]]
            assert all(x is None or math.isfinite(x) for x in numbers), f"{pair} {name}: not finite"


def test_plots_are_all_listed_and_all_present() -> None:
    """Names are compared exactly: GitHub Pages is case-sensitive and macOS is not."""
    listed = {
        f"{row['task']}/{row['model']}/{kind}.png" for row in RESULTS["rows"] for kind in row["plots"]
    }
    on_disk = {p.relative_to(SITE / "plots").as_posix() for p in (SITE / "plots").rglob("*.png")}
    assert not listed - on_disk, f"results.json lists plots that do not exist: {sorted(listed - on_disk)}"
    assert not on_disk - listed, f"plots with no result to attach to: {sorted(on_disk - listed)}"


def test_page_references_exist() -> None:
    """Every relative href and src in the shell points at a file that is published."""
    html = (SITE / "index.html").read_text(encoding="utf-8")
    for target in re.findall(r'(?:href|src)="([^"#]+)"', html):
        if re.match(r"[a-z]+:", target):
            continue
        assert (SITE / target).is_file(), f"index.html refers to {target}, which is not in site/"
