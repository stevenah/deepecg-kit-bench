"""Every integrity gate, in one place. Exit 1 kills the build before anything renders.

Each gate exists because of a specific way THIS data can lie, not as generic hygiene.
A gate that has never fired on a real mistake is decorative; the ones here are provoked
deliberately in tools/tests/test_gates.py. Messages name the offending file and say what
to do about it.
"""

from __future__ import annotations

import argparse
import hashlib
import sys

from common import (
    APPLICABILITY_KEYS,
    FIELD_FORBIDDEN_KEYS,
    FIELD_REQUIRED_KEYS,
    FORBIDDEN_MODEL_KEYS,
    MODEL_KEYS,
    ORIGIN_KEYS,
    REQUIRED_TASK_KEYS,
    TASK_KEYS,
    BuildError,
    Problem,
    build_cells,
    load_site,
    metric_vocabulary,
    read_csv,
)


def check_model_pages(site) -> list[Problem]:
    out: list[Problem] = []
    registry_names = set(site.registry.get("models", {}))
    page_names = set(site.models)

    for missing in sorted(registry_names - page_names):
        out.append(Problem(
            "E_MISSING_PAGE",
            f"deepecgkit registers '{missing}' but there is no _models/{missing}.md. An "
            f"architecture must not appear in the catalogue without prose. Write the page "
            f"(registry_name, title, family, maturity and one_liner is already a complete "
            f"page), or remove the model upstream.",
            where="_models",
        ))
    for orphan in sorted(page_names - registry_names):
        out.append(Problem(
            "E_ORPHAN_PAGE",
            f"_models/{orphan}.md has no entry in _data/registry.json. Either the model was "
            f"removed upstream (delete the page) or registry.json is stale (`make registry`).",
            where=f"_models/{orphan}.md",
        ))

    for stem, meta in sorted(site.models.items()):
        path = f"_models/{stem}.md"
        if meta.get("registry_name") != stem:
            out.append(Problem(
                "E_STEM_MISMATCH",
                f"registry_name is '{meta.get('registry_name')}' but the filename stem is "
                f"'{stem}'. They are the join key; they must be identical.",
                where=path,
            ))
        for key in sorted(MODEL_KEYS - set(meta)):
            out.append(Problem(
                "E_MISSING_FIELD",
                f"key '{key}' is absent. Liquid runs with strict_variables, so a missing key "
                f"is a build error wherever a template reads it. Optional fields must be "
                f"PRESENT AND NULL (or [] for lists), never omitted.",
                where=path,
            ))
        for key in sorted(ORIGIN_KEYS - set(meta.get("origin") or {})):
            out.append(Problem("E_MISSING_FIELD", f"origin.{key} is absent; set it null if "
                               f"unknown.", where=path))
        for key in sorted(APPLICABILITY_KEYS - set(meta.get("applicability") or {})):
            out.append(Problem("E_MISSING_FIELD", f"applicability.{key} is absent; set it null "
                               f"if unknown.", where=path))
        for key in sorted(set(meta) & FORBIDDEN_MODEL_KEYS):
            out.append(Problem(
                "E_FORBIDDEN_KEY",
                f"'{key}' is a machine fact owned by _data/registry.json or a results "
                f"snapshot, not by this file. Delete it; the template reads the generated "
                f"value. Hand-copied numbers are the drift this repo exists to prevent.",
                where=path,
            ))
        fam = meta.get("family")
        if fam is not None and fam not in site.families:
            out.append(Problem(
                "E_UNKNOWN_FAMILY",
                f"family '{fam}' is not a key in _data/families.yml "
                f"(have: {', '.join(sorted(site.families))}).",
                where=path,
            ))
        if meta.get("maturity") not in {"reference", "experimental", "deprecated", None}:
            out.append(Problem(
                "E_UNKNOWN_MATURITY",
                f"maturity '{meta.get('maturity')}' is not reference|experimental|deprecated.",
                where=path,
            ))
        if (meta.get("applicability") or {}).get("class_activation") is True:
            out.append(Problem(
                "E_CAM_CLAIM",
                f"applicability.class_activation is true, but deepecgkit implements no CAM "
                f"method (deepecgkit/explainability/attribution.py). The site must not claim "
                f"a capability the library lacks. Set it false until one exists.",
                where=path,
            ))
    return out


def check_field(site) -> list[Problem]:
    out: list[Problem] = []
    registry_names = set(site.registry.get("models", {}))
    seen: set[str] = set()
    for i, entry in enumerate(site.field):
        where = f"_data/field.yml (entry {i + 1})"
        slug = entry.get("slug")
        if not slug:
            out.append(Problem("E_FIELD_KEYS", "entry has no slug.", where=where))
            continue
        where = f"_data/field.yml ({slug})"
        if slug in seen:
            out.append(Problem("E_FIELD_DUPLICATE", f"slug '{slug}' appears twice.", where=where))
        seen.add(slug)
        if slug in registry_names:
            out.append(Problem(
                "E_FIELD_IMPLEMENTED",
                f"'{slug}' is registered in deepecgkit, so it is not a field entry any more. "
                f"Delete it from field.yml and write _models/{slug}.md -- a model must never "
                f"appear twice with two sets of facts.",
                where=where,
            ))
        for key in sorted(FIELD_REQUIRED_KEYS - set(entry)):
            out.append(Problem("E_FIELD_KEYS", f"required key '{key}' is absent.", where=where))
        for key in sorted(set(entry) & FIELD_FORBIDDEN_KEYS):
            out.append(Problem(
                "E_FIELD_FORBIDDEN",
                f"'{key}' is a measured fact, and nothing about an unimplemented model is "
                f"measured by this site. Literature-reported values belong under their own "
                f"names (params_m_reported); everything else waits for an implementation.",
                where=where,
            ))
        fam = entry.get("family")
        if fam is not None and fam not in site.families:
            out.append(Problem("E_UNKNOWN_FAMILY",
                               f"family '{fam}' is not in _data/families.yml.", where=where))
        origin = entry.get("origin") or {}
        if origin.get("paper_title") is None and origin.get("venue") is None:
            out.append(Problem(
                "E_FIELD_KEYS",
                f"entry has neither a paper_title nor a venue; a survey row with no citation "
                f"trail is an assertion, not a survey entry.",
                where=where,
            ))
    return out


def check_task_pages(site) -> list[Problem]:
    out: list[Problem] = []
    datasets = set(site.registry.get("datasets", {}))
    for stem, meta in sorted(site.tasks.items()):
        path = f"_tasks/{stem}.md"
        if meta.get("task_id") != stem:
            out.append(Problem("E_STEM_MISMATCH",
                               f"task_id is '{meta.get('task_id')}' but the stem is '{stem}'. "
                               f"(The key is task_id, not id: `id` is a reserved Jekyll "
                               f"Document property and would be shadowed.)", where=path))
        for key in sorted(TASK_KEYS - set(meta)):
            out.append(Problem(
                "E_MISSING_FIELD",
                f"key '{key}' is absent. Liquid runs with strict_variables; optional fields "
                f"must be present and null, never omitted.",
                where=path,
            ))
        ds = meta.get("registry_dataset")
        if ds is not None and ds not in datasets:
            out.append(Problem(
                "E_UNKNOWN_DATASET",
                f"registry_dataset '{ds}' is not registered in deepecgkit "
                f"(have: {', '.join(sorted(datasets))}).",
                where=path,
            ))
        pm = meta.get("primary_metric")
        if pm and pm not in site.metrics:
            out.append(Problem("E_UNKNOWN_METRIC",
                               f"primary_metric '{pm}' is not in _data/metrics.yml.", where=path))
        elif pm and pm not in metric_vocabulary(site, str(meta.get("label_mode"))):
            out.append(Problem(
                "E_METRIC_UNDEFINED_FOR_TASK",
                f"primary_metric '{pm}' is not defined for label_mode "
                f"'{meta.get('label_mode')}'. A task cannot be ranked on a metric its label "
                f"shape never produces.",
                where=path,
            ))
    return out


def check_metric_vocabulary(site) -> list[Problem]:
    """_data/metrics.yml must agree with the library's own vocabularies."""
    out: list[Problem] = []
    consts = site.registry.get("constants") or {}
    if not consts:
        return [Problem("E_NO_CONSTANTS",
                        "registry.json carries no `constants` block; run `make registry`.")]

    for kind, key in (("single_label", "single_label_metrics"),
                      ("multi_label", "multi_label_metrics")):
        lib = set(consts.get(key) or [])
        mine = {m for m, s in site.metrics.items() if kind in (s.get("vocabulary") or [])}
        for missing in sorted(lib - mine):
            out.append(Problem(
                "E_METRIC_VOCAB",
                f"deepecgkit reports '{missing}' in {key}, but _data/metrics.yml does not "
                f"list '{kind}' in its vocabulary. The site would silently drop a metric the "
                f"library computes.",
                where="_data/metrics.yml",
            ))
        for extra in sorted(mine - lib):
            out.append(Problem(
                "E_METRIC_VOCAB",
                f"_data/metrics.yml claims '{extra}' is a {kind} metric, but deepecgkit's "
                f"{key} does not include it. The site would render a column that can never "
                f"be filled.",
                where="_data/metrics.yml",
            ))

    for m in sorted(set(consts.get("lower_is_better") or [])):
        spec = site.metrics.get(m)
        if spec and spec.get("direction") != "lower":
            out.append(Problem(
                "E_DIRECTION",
                f"deepecgkit lists '{m}' in LOWER_IS_BETTER but _data/metrics.yml gives it "
                f"direction '{spec.get('direction')}'. A descending sort would invert the "
                f"calibration ranking.",
                where="_data/metrics.yml",
            ))
    for m, spec in site.metrics.items():
        if spec.get("direction") not in {"higher", "lower", "none"}:
            out.append(Problem(
                "E_DIRECTION",
                f"'{m}' has direction '{spec.get('direction')}'; must be higher|lower|none.",
                where="_data/metrics.yml",
            ))
    return out


def check_statuses(site) -> list[Problem]:
    out: list[Problem] = []
    for key, spec in site.statuses.items():
        for field in ("label", "glyph", "color_light", "color_dark"):
            if not spec.get(field):
                out.append(Problem(
                    "E_STATUS_FIELD",
                    f"status '{key}' is missing '{field}'. Both colours are mandatory -- a "
                    f"single colour cannot survive the theme toggle -- and the glyph is what "
                    f"makes status legible without colour at all.",
                    where="_data/statuses.yml",
                ))
        bucket = spec.get("bucket")
        if not bucket:
            out.append(Problem(
                "E_STATUS_BUCKET",
                f"status '{key}' declares no 'bucket'. The legend groups statuses into the "
                f"buckets in _data/buckets.yml; a status outside every bucket would render "
                f"on cells but appear in no legend entry.",
                where="_data/statuses.yml",
            ))
        elif bucket not in site.buckets:
            out.append(Problem(
                "E_STATUS_BUCKET",
                f"status '{key}' names bucket '{bucket}', which is not a key in "
                f"_data/buckets.yml (have: {', '.join(sorted(site.buckets))}).",
                where="_data/statuses.yml",
            ))
        else:
            # Colour belongs to the bucket. If a status could carry its own, two cells the
            # same colour could sit in different legend buckets and the legend would lie.
            bspec = site.buckets[bucket]
            for field in ("color_light", "color_dark"):
                if spec.get(field) and spec[field] != bspec.get(field):
                    out.append(Problem(
                        "E_STATUS_BUCKET_COLOUR",
                        f"status '{key}' has {field} {spec[field]} but its bucket "
                        f"'{bucket}' has {bspec.get(field)}. A status must repeat its "
                        f"bucket's colours exactly -- the legend shows one swatch per "
                        f"bucket, so a status that renders a different colour is "
                        f"unaccounted for in the legend.",
                        where="_data/statuses.yml",
                    ))
    return out


def check_buckets(site) -> list[Problem]:
    out: list[Problem] = []
    if not site.buckets:
        out.append(Problem(
            "E_NO_BUCKETS",
            "_data/buckets.yml is empty or missing. The coverage legend renders from it.",
            where="_data/buckets.yml",
        ))
        return out
    for key, spec in site.buckets.items():
        for field in ("label", "glyph", "color_light", "color_dark", "order"):
            if spec.get(field) in (None, ""):
                out.append(Problem(
                    "E_BUCKET_FIELD",
                    f"bucket '{key}' is missing '{field}'.",
                    where="_data/buckets.yml",
                ))
    orders = [b.get("order") for b in site.buckets.values()]
    if len(set(orders)) != len(orders):
        out.append(Problem(
            "E_BUCKET_ORDER",
            f"two buckets share an 'order' ({orders}); legend ordering would be arbitrary.",
            where="_data/buckets.yml",
        ))
    for key in site.buckets:
        if not any(s.get("bucket") == key for s in site.statuses.values()):
            out.append(Problem(
                "E_BUCKET_ORPHAN",
                f"bucket '{key}' is claimed by no status in _data/statuses.yml, so it can "
                f"never appear on a cell. Delete it or give a status that bucket.",
                where="_data/buckets.yml",
            ))
    return out


def check_reported(site) -> list[Problem]:
    """_data/reported.yml: published values that fill cells this site has not measured.

    Every gate here exists because a wrong row would put someone else's number into a table
    that reads as this site's own measurements.
    """
    out: list[Problem] = []
    registry = set(site.registry.get("models", {}))
    field_slugs = {str(e.get("slug")) for e in (site.field or [])}
    seen: set[tuple[str, str, str]] = set()

    measured_pairs = {
        (c["model"], c["task"])
        for c in build_cells(site)[0]
        if site.statuses.get(c["status"], {}).get("bucket") == "kit"
    }

    for i, r in enumerate(site.reported or []):
        where = f"_data/reported.yml (entry {i + 1})"
        model, task = str(r.get("model") or ""), str(r.get("task") or "")
        metric = str(r.get("metric") or "")
        if not (model and task and metric):
            out.append(Problem("E_REPORTED_KEYS",
                               "entry needs 'model', 'task' and 'metric'.", where=where))
            continue
        where = f"_data/reported.yml ({model} x {task}, {metric})"

        if model not in registry and model not in field_slugs:
            out.append(Problem(
                "E_REPORTED_MODEL",
                f"'{model}' is neither a registered model nor a _data/field.yml slug.",
                where=where))
        if task not in site.tasks:
            out.append(Problem(
                "E_REPORTED_TASK",
                f"'{task}' is not a task_id in _tasks/ (have: {', '.join(sorted(site.tasks))}).",
                where=where))
        elif metric not in metric_vocabulary(site, str(site.tasks[task].get("label_mode"))):
            out.append(Problem(
                "E_REPORTED_METRIC",
                f"'{metric}' is not defined for the {site.tasks[task].get('label_mode')} "
                f"task '{task}'. Recording it would invent a number the metric vocabulary "
                f"says cannot exist for this label shape.",
                where=where))

        if r.get("value") is None:
            out.append(Problem("E_REPORTED_VALUE",
                               "entry has no 'value'. A reported row with no number is a "
                               "citation, not a result; put it in _data/field.yml instead.",
                               where=where))

        src = r.get("source") or {}
        if not (src.get("paper_title") or src.get("doi")):
            out.append(Problem(
                "E_REPORTED_SOURCE",
                "entry has neither source.paper_title nor source.doi. An unattributed "
                "published number cannot be checked by a reader and must not render.",
                where=where))

        key = (model, task, metric)
        if key in seen:
            out.append(Problem("E_REPORTED_DUPLICATE",
                               f"({model}, {task}, {metric}) appears twice.", where=where))
        seen.add(key)

        if (model, task) in measured_pairs:
            out.append(Problem(
                "E_REPORTED_SHADOWED",
                f"this site has measured ({model}, {task}), so the measurement wins and this "
                f"row can never render. Delete it rather than leaving a value in the file "
                f"that silently does nothing.",
                where=where))
    return out


def check_snapshot(site) -> list[Problem]:
    out: list[Problem] = []
    d = site.snapshot_dir

    checksums = d / "CHECKSUMS.sha256"
    if not checksums.is_file():
        out.append(Problem("E_NO_CHECKSUMS",
                           f"{checksums} is missing; the snapshot cannot be trusted or cited.",
                           where=str(d)))
    else:
        for line in checksums.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            digest, _, name = line.partition("  ")
            f = d / name.strip()
            if not f.is_file():
                out.append(Problem("E_CHECKSUM",
                                   f"{name.strip()} is listed in CHECKSUMS but missing.",
                                   where=str(d)))
                continue
            h = hashlib.sha256()
            with f.open("rb") as fh:
                for chunk in iter(lambda: fh.read(65536), b""):
                    h.update(chunk)
            if h.hexdigest() != digest:
                out.append(Problem(
                    "E_CHECKSUM",
                    f"{name.strip()} does not match its recorded digest: a results file was "
                    f"edited after the manifest was written. Snapshots are immutable -- "
                    f"rebuild with tools/make_snapshot.py under a new id.",
                    where=str(d),
                ))

    protocol = site.manifest.get("protocol") or {}
    status = site.manifest.get("status")
    if protocol.get("include_legacy") and status not in {"preliminary", "archival"}:
        out.append(Problem(
            "E_LEGACY_STATUS",
            f"snapshot '{site.snapshot_id}' pooled seedless runs (include_legacy) but is "
            f"declared '{status}'. Seedless runs must never sit beside real replicates in a "
            f"snapshot presented as current.",
            where=str(d / "manifest.yml"),
        ))

    # Averaging homogeneity per (dataset, metric). reconcile_averaging() groups by
    # (dataset, model), so it CANNOT see a binary F1 beside a macro F1 in the same column of
    # the same table -- which is exactly the comparison a leaderboard invites.
    seen: dict[tuple[str, str], set[str]] = {}
    for r in site.metric_rows:
        if not (site.metrics.get(r["metric"]) or {}).get("averaging_sensitive"):
            continue
        seen.setdefault((r["dataset"], r["metric"]), set()).add(r.get("averaging") or "unknown")
    for (ds, metric), modes in sorted(seen.items()):
        if len(modes) > 1:
            out.append(Problem(
                "E_MIXED_AVERAGING",
                f"dataset '{ds}' metric '{metric}' mixes averaging modes {sorted(modes)} in "
                f"one column. Precision, recall and F1 are not comparable across modes, so "
                f"this table would rank incommensurable numbers.",
                where=str(d / "seed_metrics_long.csv"),
            ))

    # Declared vs observed averaging. resolve_average() silently returns "binary" when the
    # realised test split holds <=2 classes, so a task can flip mode with nobody editing
    # anything. "unknown" means unrecorded, not conflicting, so it does not trip this.
    observed: dict[str, set[str]] = {}
    for r in site.metric_rows:
        observed.setdefault(r["dataset"], set()).add(r.get("averaging") or "unknown")
    for tid, task in sorted(site.tasks.items()):
        ds = str(task.get("registry_dataset"))
        declared = task.get("expected_averaging")
        got = {a for a in observed.get(ds, set()) if a and a != "unknown"}
        if got and declared and declared not in got:
            out.append(Problem(
                "E_AVERAGING_MISMATCH",
                f"task declares expected_averaging '{declared}' but the snapshot observed "
                f"{sorted(got)} for dataset '{ds}'. Either the split changed shape or the "
                f"declaration is wrong; both change what the numbers mean.",
                where=f"_tasks/{tid}.md",
            ))

    # aggregate and rank are two separate invocations. If they saw different data, the
    # ranking describes a table that is not the one on screen.
    ranks = read_csv(d / "seed_ranks.csv")
    if ranks:
        run_keys = {(r["dataset"], r["model"], r["seed"]) for r in site.run_rows}
        rank_keys = {(r["dataset"], r["model"], r["seed"]) for r in ranks}
        if rank_keys - run_keys or run_keys - rank_keys:
            out.append(Problem(
                "E_KEYSET_MISMATCH",
                f"seed_ranks.csv and seed_runs_long.csv disagree on which runs exist "
                f"({len(rank_keys - run_keys)} only in ranks, {len(run_keys - rank_keys)} only "
                f"in runs). Both commands must run with identical flags over identical roots.",
                where=str(d),
            ))

    unknown = sorted({r["metric"] for r in site.metric_rows if r["metric"] not in site.metrics})
    for m in unknown:
        out.append(Problem(
            "E_UNKNOWN_METRIC",
            f"snapshot contains metric '{m}', absent from _data/metrics.yml, so the site "
            f"cannot know its direction or its label.",
            where=str(d / "seed_metrics_long.csv"),
        ))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--registry-only", action="store_true",
                    help="Only the registry<->_models gates (used by the refresh bot's PR)")
    args = ap.parse_args(argv)

    try:
        site = load_site()
    except BuildError as exc:
        print(f"E_LOAD: {exc}", file=sys.stderr)
        return 1

    problems = list(check_model_pages(site))
    if not args.registry_only:
        problems += check_field(site)
        problems += check_task_pages(site)
        problems += check_metric_vocabulary(site)
        problems += check_buckets(site)
        problems += check_statuses(site)
        problems += check_reported(site)
        problems += check_snapshot(site)
        problems += build_cells(site)[1]

    if problems:
        print(f"\n{len(problems)} problem(s):\n", file=sys.stderr)
        for p in problems:
            print(f"  {p}\n", file=sys.stderr)
        return 1

    n_cells = len(site.registry.get("models", {})) * len(site.tasks)
    print(
        f"validate: OK\n"
        f"  models     {len(site.models)} pages == "
        f"{len(site.registry.get('models', {}))} registered\n"
        f"  survey     {len(site.field)} field entries, none colliding\n"
        f"  reported   {len(site.reported)} published values, "
        f"{len(site.buckets)} legend buckets\n"
        f"  tasks      {len(site.tasks)}\n"
        f"  cells      {n_cells} (all statused)\n"
        f"  snapshot   {site.snapshot_id} ({site.manifest.get('status')}), checksums verified"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
