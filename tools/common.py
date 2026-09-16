"""Shared loading and the cell-universe computation.

Both tools/validate.py and tools/build_site_data.py import this, so the rules they
enforce and the data the site renders are computed by the same code. If they were
separate implementations, the validator could pass while the renderer produced something
different -- which is exactly the failure mode this repo exists to prevent.
"""

from __future__ import annotations

import csv
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
FRONT_MATTER = re.compile(r"^---\n(.*?)\n---", re.DOTALL)

# Keys that name a machine fact. If one of these appears in _models/*.md, some human has
# copied a number out of the registry or a results CSV into prose, creating a second copy
# that can go stale silently. The build refuses.
FORBIDDEN_MODEL_KEYS = {
    "params", "params_m", "params_total", "params_trainable", "feature_dim",
    "min_input_length", "max_input_length", "head_attr", "class", "class_name",
    "module", "default_kwargs", "pretrained_weights", "cam_applicable",
    "f1", "auroc", "accuracy", "mcc", "precision", "recall", "best_score", "rank",
}

# Under Liquid's strict_variables a missing key is a hard build error, including on a plain
# hash. That is a feature -- it means a template can never silently render an empty string
# where a fact should be -- but the raw Liquid message names a line number, not a fix. So the
# full key set is declared here and checked by validate.py, which can say which file is
# missing what. Optional keys must be PRESENT AND NULL, never absent.
REQUIRED_MODEL_KEYS = {"registry_name", "title", "family", "maturity", "one_liner", "applicability"}
OPTIONAL_MODEL_KEYS = {
    "order", "search_keywords", "origin", "implementation_notes",
    "deviations_from_paper", "sections",
}
MODEL_KEYS = REQUIRED_MODEL_KEYS | OPTIONAL_MODEL_KEYS
ORIGIN_KEYS = {"paper_title", "authors", "venue", "year", "doi", "code_url", "adapted_from"}
APPLICABILITY_KEYS = {"gradient_attribution", "occlusion", "class_activation", "notes"}

# The field survey (_data/field.yml): architectures NOT implemented in deepecgkit. They may
# carry only literature-reported facts. A measured-fact key on a survey entry means someone
# is hand-maintaining a number this site elsewhere derives -- refuse it. And a survey slug
# that matches a registered model means the entry is stale: the model got implemented, so
# the entry must be deleted and written up as _models/<slug>.md instead.
FIELD_REQUIRED_KEYS = {"slug", "title", "family", "one_liner", "params_m_reported",
                       "search_keywords", "origin"}
FIELD_FORBIDDEN_KEYS = {
    "params", "params_m", "params_total", "params_trainable", "feature_dim",
    "min_input_length", "max_input_length", "head_attr", "class", "module",
    "default_kwargs", "tasks_measured", "f1", "auroc", "accuracy", "mcc", "rank",
    "registry_name", "maturity",
}

REQUIRED_TASK_KEYS = {
    "task_id", "title", "registry_dataset", "label_mode", "expected_averaging",
    "replicate_kind", "expected_replicates", "primary_metric",
}
OPTIONAL_TASK_KEYS = {
    "short_title", "order", "in_journal", "scope", "probe", "summary",
    "split_protocol", "replicate_note", "dataset_url", "ecgbench_url",
}
TASK_KEYS = REQUIRED_TASK_KEYS | OPTIONAL_TASK_KEYS

LABEL_MODE_VOCAB = {
    "multi_label": "multi_label",
    "single_label": "single_label",
    "binary": "single_label",   # binary tasks use the single-label metric vocabulary
}


class BuildError(Exception):
    """A gate failed. The message names the offending file and what to do about it."""


@dataclass
class Problem:
    code: str
    message: str
    where: str = ""

    def __str__(self) -> str:
        loc = f" [{self.where}]" if self.where else ""
        return f"{self.code}{loc}: {self.message}"


def read_front_matter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    m = FRONT_MATTER.match(text)
    if not m:
        raise BuildError(
            f"{path}: no YAML front matter. The file must begin with '---', hold YAML, "
            f"and close with a line containing only '---'."
        )
    return yaml.safe_load(m.group(1)) or {}


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def flatten_reported(raw: Any) -> list[dict[str, Any]]:
    """Accept _data/reported.yml in either shape and return flat rows.

    Grouped (preferred) puts one paper's whole table in one block, so a source and its
    protocol note are written once instead of being copy-pasted onto every value -- which is
    what made the flat form miserable to extend, and what let a note drift out of step with
    the source beside it:

        - source: {paper_title: ..., doi: ...}
          protocol_note: "applies to every value below"
          values:
            - {model: st-mem, task: ptbxl-multilabel, metric: f1, value: 0.662, n: null}

    Flat rows (a `model` key at top level) still work, so nothing downstream -- and no
    existing row -- has to change. A value may set its own `protocol_note` to override the
    block's where one line needs saying differently.
    """
    out: list[dict[str, Any]] = []
    for block in raw or []:
        if not isinstance(block, dict) or "values" not in block:
            out.append(block)
            continue
        src, note = block.get("source") or {}, block.get("protocol_note")
        for v in block.get("values") or []:
            row = dict(v)
            row.setdefault("source", src)
            if row.get("protocol_note") in (None, ""):
                row["protocol_note"] = note
            out.append(row)
    return out


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def to_float(v: Any) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def to_int(v: Any) -> int | None:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


@dataclass
class Site:
    root: Path
    registry: dict[str, Any]
    models: dict[str, dict[str, Any]]
    tasks: dict[str, dict[str, Any]]
    families: dict[str, Any]
    metrics: dict[str, Any]
    statuses: dict[str, Any]
    buckets: dict[str, Any]
    known_defects: list[dict[str, Any]]
    field: list[dict[str, Any]]
    reported: list[dict[str, Any]]
    snapshot_id: str
    snapshot_dir: Path
    manifest: dict[str, Any]
    metric_rows: list[dict[str, str]]
    run_rows: list[dict[str, str]]
    rank_rows: list[dict[str, str]]
    problems: list[Problem] = field(default_factory=list)

    @property
    def kit_version(self) -> str | None:
        return (self.registry.get("meta") or {}).get("kit_version")


def load_site(root: Path = ROOT) -> Site:
    reg_path = root / "_data" / "registry.json"
    if not reg_path.is_file():
        raise BuildError(
            f"{reg_path} is missing. Generate it with:\n"
            f"  make registry\n"
            f"It is the sole source of every machine fact about a model, and the site "
            f"cannot render without it."
        )
    registry = load_json(reg_path)

    models = {}
    for p in sorted((root / "_models").glob("*.md")):
        models[p.stem] = {"__path": p, **read_front_matter(p)}
    tasks = {}
    for p in sorted((root / "_tasks").glob("*.md")):
        tasks[p.stem] = {"__path": p, **read_front_matter(p)}

    snapshots = load_yaml(root / "_data" / "snapshots.yml") or {}
    snapshot_id = snapshots.get("current")
    snapshot_dir = root / "results" / "snapshots" / str(snapshot_id)
    manifest_path = snapshot_dir / "manifest.yml"
    if not manifest_path.is_file():
        raise BuildError(
            f"_data/snapshots.yml names current snapshot '{snapshot_id}', but "
            f"{manifest_path} does not exist. Either build it with tools/make_snapshot.py "
            f"or point `current:` at a snapshot that is committed."
        )

    return Site(
        root=root,
        registry=registry,
        models=models,
        tasks=tasks,
        families=load_yaml(root / "_data" / "families.yml") or {},
        metrics=load_yaml(root / "_data" / "metrics.yml") or {},
        statuses=load_yaml(root / "_data" / "statuses.yml") or {},
        buckets=load_yaml(root / "_data" / "buckets.yml") or {},
        known_defects=load_yaml(root / "_data" / "known_defects.yml") or [],
        field=(load_yaml(root / "_data" / "field.yml") or []) if (root / "_data" / "field.yml").is_file() else [],
        reported=flatten_reported(
            load_yaml(root / "_data" / "reported.yml")
            if (root / "_data" / "reported.yml").is_file() else []
        ),
        snapshot_id=str(snapshot_id),
        snapshot_dir=snapshot_dir,
        manifest=load_yaml(manifest_path) or {},
        metric_rows=read_csv(snapshot_dir / "seed_metrics_long.csv"),
        run_rows=read_csv(snapshot_dir / "seed_runs_long.csv"),
        rank_rows=read_csv(snapshot_dir / "rank_distribution.csv"),
    )


# --------------------------------------------------------------------------------------
# The cell universe
# --------------------------------------------------------------------------------------

def metric_vocabulary(site: Site, label_mode: str) -> set[str]:
    """Which metrics are defined for a task's label shape."""
    want = LABEL_MODE_VOCAB.get(label_mode, "single_label")
    return {k for k, v in site.metrics.items() if want in (v.get("vocabulary") or [])}


def defects_for(site: Site, dataset: str) -> list[dict[str, Any]]:
    """Known defects that apply to this dataset at the snapshot's kit version."""
    out = []
    kit = site.kit_version or ""
    for d in site.known_defects:
        if dataset not in (d.get("datasets") or []):
            continue
        cap = d.get("kit_version_max")
        if cap and kit and _version_tuple(kit) > _version_tuple(cap):
            continue
        out.append(d)
    return out


def _version_tuple(v: str) -> tuple[int, ...]:
    parts = []
    for chunk in str(v).split("."):
        num = "".join(c for c in chunk if c.isdigit())
        parts.append(int(num) if num else 0)
    return tuple(parts) or (0,)


def build_cells(site: Site) -> tuple[list[dict[str, Any]], list[Problem]]:
    """One record per (model, task). Every record carries exactly one status.

    A cell is never absent and never blank: if we have no number, the record says which
    of the several different reasons applies. That is the machine-checked form of the
    journal's rule that no cell may be left blank.
    """
    problems: list[Problem] = []

    # dataset -> task. A legacy metrics CSV records only `dataset`, so a dataset serving
    # two tasks would make its rows unattributable. Enforce the constraint rather than
    # silently attributing them to whichever task sorts first.
    by_dataset: dict[str, list[str]] = {}
    for tid, t in site.tasks.items():
        by_dataset.setdefault(str(t.get("registry_dataset")), []).append(tid)
    for ds, tids in by_dataset.items():
        if len(tids) > 1:
            problems.append(Problem(
                "E_AMBIGUOUS_DATASET",
                f"dataset '{ds}' is claimed by {len(tids)} tasks ({', '.join(sorted(tids))}). "
                f"classification_metrics.csv records only the dataset name, so its rows "
                f"cannot be attributed to one task. Give each task a distinct "
                f"registry_dataset, or add a task discriminator upstream first.",
                where="_tasks",
            ))

    # (dataset, model, metric) -> aggregated row
    agg: dict[tuple[str, str, str], dict[str, str]] = {}
    for r in site.metric_rows:
        agg[(r["dataset"], r["model"], r["metric"])] = r

    incomplete = {
        (i.get("model"), i.get("dataset"))
        for i in (site.manifest.get("incomplete_runs") or [])
        if i.get("model")
    }

    # (model, task, metric) -> the published value. Literature facts from _data/reported.yml,
    # kept in a separate lookup because they may only ever fill a cell we have NOT measured.
    reported_by: dict[tuple[str, str, str], dict[str, Any]] = {}
    for r in site.reported or []:
        reported_by[(str(r.get("model")), str(r.get("task")), str(r.get("metric")))] = r

    cells: list[dict[str, Any]] = []
    for name in sorted(site.registry.get("models", {})):
        editorial = site.models.get(name, {})
        for tid, task in sorted(site.tasks.items(), key=lambda kv: kv[1].get("order", 999)):
            ds = str(task.get("registry_dataset"))
            primary = str(task.get("primary_metric", "f1"))
            expected = to_int(task.get("expected_replicates")) or 0
            vocab = metric_vocabulary(site, str(task.get("label_mode")))

            row = agg.get((ds, name, primary))
            cell: dict[str, Any] = {
                "model": name,
                "model_title": editorial.get("title", name),
                "task": tid,
                "task_title": task.get("short_title") or task.get("title"),
                "dataset": ds,
                "metric": primary,
                "value": None, "sd": None, "n": 0,
                "lower_ci": None, "upper_ci": None,
                "averaging": None,
                "expected_replicates": expected,
                "flags": [],
                # Always present, even when empty: Liquid's strict_variables makes a missing
                # key a build error, so every generated record must be TOTAL -- same keys on
                # every row, regardless of status.
                "reason": "",
                # Pre-formatted for display: see build_site_data.fmt. Keeps a measured
                # zero looking like a measurement instead of a rounding artefact.
                "display": "--",
                "defects": [d["id"] for d in defects_for(site, ds)],
                "status": None,
                # Filled only for a `reported` cell, but present on every row: strict_variables
                # makes a missing key a build error even on a hash the template never reaches.
                "reported_paper": "",
                "reported_doi": "",
                "protocol_note": "",
                # Published values for a metric OTHER than this cell's. Pre-formatted, and
                # empty on almost every row -- but present on all of them, because
                # strict_variables makes a missing key a build error.
                "reported_other": "",
                # False for every model DeepECG-Kit registers. Survey architectures get
                # cells too (see below), but they are a different kind of row: nothing about
                # them is or ever will be measured here, so they are excluded from the
                # coverage denominator and from the coverage matrix.
                "is_survey": False,
            }

            if primary not in vocab:
                cell["status"] = "metric_undefined"
                cell["reason"] = (
                    f"{primary} is not defined for a {task.get('label_mode')} task."
                )
            elif row is not None:
                n = to_int(row.get("n")) or 0
                _v = to_float(row.get("mean"))
                _p = (site.metrics.get(primary) or {}).get("precision", 3)
                cell.update({
                    "value": _v,
                    "display": "--" if _v is None else f"{_v:.{_p}f}",
                    "sd": to_float(row.get("std")),
                    "n": n,
                    "lower_ci": to_float(row.get("lower_ci")),
                    "upper_ci": to_float(row.get("upper_ci")),
                    "averaging": row.get("averaging") or "unknown",
                })
                # A direct reading of the committed numbers, NOT a convergence verdict:
                # the site never re-implements the library's criterion. See methodology.
                prec = to_float((agg.get((ds, name, "precision")) or {}).get("mean"))
                rec = to_float((agg.get((ds, name, "recall")) or {}).get("mean"))
                if prec == 0.0 and rec == 0.0:
                    cell["flags"].append("zero_predicted_positives")
                # No snapshot carries a convergence column yet (Phase 6 PR 2 adds one), so
                # we can only say we do not know -- never that it converged.
                if not (site.manifest.get("schema_flags") or {}).get("convergence_present"):
                    cell["status"] = "convergence_unknown" if n >= expected else "partial"
                else:
                    cell["status"] = "measured" if n >= expected else "partial"
                if n < expected:
                    cell["status"] = "partial"
            elif (name, ds) in incomplete:
                cell["status"] = "incomplete"
                cell["reason"] = "A run directory exists but produced no metrics file."
            else:
                cell["status"] = "not_run"
                cell["reason"] = "This model has never been trained on this task."

            # A published value fills the gap where this site has measured nothing -- and only
            # there. A measurement always outranks a paper's number, because the measurement
            # was produced under the protocol the rest of the table is comparable with.
            rep = reported_by.get((name, tid, primary))
            if rep is not None and cell["status"] in ("not_run", "incomplete"):
                _rv = to_float(rep.get("value"))
                _rp = (site.metrics.get(primary) or {}).get("precision", 3)
                src = rep.get("source") or {}
                note = str(rep.get("protocol_note") or "").strip()
                cell.update({
                    "value": _rv,
                    "display": "--" if _rv is None else f"{_rv:.{_rp}f}",
                    "n": to_int(rep.get("n")) or 0,
                    "status": "reported",
                    "reported_paper": str(src.get("paper_title") or ""),
                    "reported_doi": str(src.get("doi") or ""),
                    "protocol_note": note,
                    "reason": (
                        f"Reported by the original authors, not measured here."
                        + (f" {note}" if note else "")
                    ),
                })
            elif cell["status"] in ("not_run", "incomplete"):
                # A published value for some OTHER metric. It cannot fill this cell -- the
                # cell shows the task's primary metric and that is what has not been measured
                # -- but hiding it would leave a reader on /coverage/ or a model page unaware
                # that a number exists at all. So the status stays honest and the citation is
                # surfaced beside the reason. Most of the ECG literature reports macro-AUC
                # where this site ranks on macro-F1, so this is the common case, not the edge.
                others = sorted(
                    ((m, r) for (mo, t, m), r in reported_by.items()
                     if mo == name and t == tid and m != primary),
                    key=lambda pair: pair[0],
                )
                if others:
                    src = (others[0][1].get("source") or {})
                    cell.update({
                        "reported_paper": str(src.get("paper_title") or ""),
                        "reported_doi": str(src.get("doi") or ""),
                        "protocol_note": str(others[0][1].get("protocol_note") or "").strip(),
                        "reported_other": "; ".join(
                            f"{m} {to_float(r.get('value')):.{(site.metrics.get(m) or {}).get('precision', 3)}f}"
                            for m, r in others if to_float(r.get("value")) is not None
                        ),
                    })

            if cell["status"] is None:
                problems.append(Problem(
                    "E_UNSTATUSED_CELL",
                    f"cell ({name}, {tid}) has no status. Every cell must carry exactly "
                    f"one status from _data/statuses.yml.",
                ))
            elif cell["status"] not in site.statuses:
                problems.append(Problem(
                    "E_UNKNOWN_STATUS",
                    f"cell ({name}, {tid}) has status '{cell['status']}', which is not a "
                    f"key in _data/statuses.yml.",
                ))
            cells.append(cell)

    # ---- Survey architectures -------------------------------------------------------
    # A _data/field.yml entry is not implemented here, so it has no run and never will.
    # It therefore gets a cell ONLY where a published value exists for it -- the cell is
    # created BY the citation rather than by the model x task grid. Two consequences that
    # keep the rest of the site honest:
    #
    #   * the grid stays 21 x 5. Materialising 161 survey architectures against every task
    #     would add ~800 cells that are all "not run" in a sense that means nothing (we were
    #     never going to run them), drowning the coverage signal it exists to show.
    #   * these cells are `is_survey`, and build_coverage keeps them out of the denominator.
    #     Citing a paper must not move a percentage that describes what this site measured.
    #
    # The cell's metric is whichever one the paper actually reports, not the task's primary
    # metric: most ECG papers publish macro-AUC where this site ranks on macro-F1, and a
    # survey row carrying an empty F1 would say nothing at all.
    field_by_slug = {str(e.get("slug")): e for e in (site.field or [])}
    survey_rows: dict[tuple[str, str], list[tuple[str, dict[str, Any]]]] = {}
    for (mo, tid, metric), r in reported_by.items():
        if mo in field_by_slug and tid in site.tasks:
            survey_rows.setdefault((mo, tid), []).append((metric, r))

    for (mo, tid), entries in sorted(survey_rows.items()):
        entry = field_by_slug[mo]
        task = site.tasks[tid]
        ds = str(task.get("registry_dataset"))
        primary = str(task.get("primary_metric", "f1"))
        # Prefer the task's primary metric when the paper happens to report it, so a survey
        # row lands in the same column as the measured ones wherever it legitimately can.
        entries.sort(key=lambda kv: (kv[0] != primary, kv[0]))
        metric, rep = entries[0]
        prec = (site.metrics.get(metric) or {}).get("precision", 3)
        val = to_float(rep.get("value"))
        src = rep.get("source") or {}
        note = str(rep.get("protocol_note") or "").strip()
        others = [(m, r) for m, r in entries[1:]]
        cells.append({
            "model": mo,
            "model_title": entry.get("title", mo),
            "task": tid,
            "task_title": task.get("short_title") or task.get("title"),
            "dataset": ds,
            "metric": metric,
            "value": val,
            "display": "--" if val is None else f"{val:.{prec}f}",
            "sd": None,
            "n": to_int(rep.get("n")) or 0,
            "lower_ci": None, "upper_ci": None,
            "averaging": None,
            "expected_replicates": to_int(task.get("expected_replicates")) or 0,
            "flags": [],
            "defects": [d["id"] for d in defects_for(site, ds)],
            "status": "reported",
            "reported_paper": str(src.get("paper_title") or ""),
            "reported_doi": str(src.get("doi") or ""),
            "protocol_note": note,
            "reported_other": "; ".join(
                f"{m} {to_float(r.get('value')):.{(site.metrics.get(m) or {}).get('precision', 3)}f}"
                for m, r in others if to_float(r.get("value")) is not None
            ),
            "reason": (
                "Not implemented in DeepECG-Kit. Reported by the original authors."
                + (f" {note}" if note else "")
            ),
            "is_survey": True,
        })

    return cells, problems
