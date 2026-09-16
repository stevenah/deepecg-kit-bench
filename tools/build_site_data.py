"""Build _data/generated/*.json, the generated colour tokens, and the inline SVG charts.

Everything the site renders comes from here, so a table and the chart beside it cannot
disagree -- they are the same numbers formatted twice. (ECGBench's own charts hardcode
their values in a script block underneath a Liquid-rendered table; that drift is the bug
this design exists to avoid.)

Charts are emitted as SVG and inlined by Liquid with {% include %}, never referenced with
<img src>. An SVG loaded through <img> is an isolated document: it sees neither the page
stylesheet nor :root[data-theme], so currentColor resolves to black and every CSS
variable is undefined. Inlined, theme switching is a pure custom-property cascade and no
JavaScript touches a chart at all.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from common import ROOT, BuildError, build_cells, load_site, metric_vocabulary, to_float, to_int

GEN_DATA = ROOT / "_data" / "generated"
GEN_SVG = ROOT / "_includes" / "charts" / "generated"
GEN_CSS = ROOT / "assets" / "css" / "generated"


PROBE_FIELDS = ("status", "params_total", "params_trainable", "feature_dim", "reason")


def total_probe(p: dict[str, Any]) -> dict[str, Any]:
    """Normalise a probe record so every key is present.

    Liquid runs with strict_variables, so a template reading .reason on a successful probe
    would be a build error unless the key exists. Generated records are always total.
    """
    return {k: p.get(k) for k in PROBE_FIELDS}


def esc(s: Any) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def fmt(v: float | None, precision: int = 3) -> str:
    return "--" if v is None else f"{v:.{precision}f}"


# --------------------------------------------------------------------------------------
# JSON payloads
# --------------------------------------------------------------------------------------

def build_catalogue(site, cells) -> dict[str, Any]:
    canonical = (site.registry.get("meta") or {}).get("canonical_probe", "12x5")
    measured_by_model: dict[str, int] = {}
    for c in cells:
        # "Tasks measured" counts this site's own runs. A paper-reported value is a number,
        # but it is not a measurement made here, so it must not raise this column.
        st = site.statuses.get(c["status"], {})
        if st.get("shows_number") and st.get("bucket") == "kit":
            measured_by_model[c["model"]] = measured_by_model.get(c["model"], 0) + 1

    rows = []
    for name, reg in sorted(site.registry.get("models", {}).items()):
        ed = site.models.get(name, {})
        probe = total_probe((reg.get("probes") or {}).get(canonical, {}))
        fam = str(ed.get("family", ""))
        rows.append({
            "registry_name": name,
            "title": ed.get("title") or reg.get("display_name") or name,
            "family": fam,
            "family_label": (site.families.get(fam) or {}).get("label", fam),
            "family_order": (site.families.get(fam) or {}).get("order", 999),
            "order": ed.get("order", 999),
            "maturity": ed.get("maturity"),
            "one_liner": ed.get("one_liner", ""),
            "search_keywords": ed.get("search_keywords", ""),
            "description": reg.get("description", ""),
            "class": reg.get("class"),
            "module": reg.get("module"),
            "head_attr": reg.get("head_attr"),
            "min_input_length": reg.get("min_input_length"),
            "max_input_length": reg.get("max_input_length"),
            "params_total": probe.get("params_total"),
            "params_m": (round(probe["params_total"] / 1e6, 2)
                         if probe.get("params_total") else None),
            "feature_dim": probe.get("feature_dim"),
            "probe_status": probe.get("status"),
            # A list, not a hash: iterating a hash in Liquid yields [k, v] pairs that must
            # be indexed positionally, which is both unreadable and fragile under
            # strict_variables. Generated data is shaped for the template that consumes it.
            "probes": [
                dict(total_probe(v), shape=k)
                for k, v in sorted((reg.get("probes") or {}).items())
            ],
            "tasks_measured": measured_by_model.get(name, 0),
            "origin": ed.get("origin") or {},
            "applicability": ed.get("applicability") or {},
        })
    rows.sort(key=lambda r: (r["family_order"], r["params_total"] or 0))

    # The survey: kit models and field entries in ONE table, distinguished by a flag.
    # Rows are TOTAL (same keys everywhere -- strict Liquid) and sorted the way a survey
    # reads: family, then publication year, then name.
    def _origin(o):
        keys = ("paper_title", "authors", "venue", "year", "doi", "code_url", "adapted_from")
        o = o or {}
        return {k: o.get(k) for k in keys}

    survey: list[dict[str, Any]] = []
    for r in rows:
        survey.append({
            "slug": r["registry_name"],
            "title": r["title"],
            "implemented": True,
            "registry_name": r["registry_name"],
            "family": r["family"],
            "family_label": r["family_label"],
            "family_order": r["family_order"],
            "year": (r["origin"] or {}).get("year"),
            "one_liner": r["one_liner"],
            "search_keywords": r["search_keywords"],
            "params_m": r["params_m"],
            "params_kind": "measured" if r["params_m"] is not None else None,
            "tasks_measured": r["tasks_measured"],
            "origin": _origin(r["origin"]),
        })
    for e in site.field:
        fam = str(e.get("family", ""))
        famspec = site.families.get(fam) or {}
        reported = e.get("params_m_reported")
        survey.append({
            "slug": e.get("slug"),
            "title": e.get("title"),
            "implemented": False,
            "registry_name": None,
            "family": fam,
            "family_label": famspec.get("label", fam),
            "family_order": famspec.get("order", 999),
            "year": (e.get("origin") or {}).get("year"),
            "one_liner": e.get("one_liner", ""),
            "search_keywords": e.get("search_keywords", ""),
            "params_m": reported,
            "params_kind": "reported" if reported is not None else None,
            "tasks_measured": None,
            "origin": _origin(e.get("origin")),
        })
    survey.sort(key=lambda r: (r["family_order"], r["year"] or 9999, str(r["title"]).lower()))

    families = [
        {"key": k, "label": v.get("label", k), "order": v.get("order", 999),
         "blurb": v.get("blurb", ""),
         "count": sum(1 for r in survey if r["family"] == k),
         "count_implemented": sum(1 for r in survey if r["family"] == k and r["implemented"]),
         "count_field": sum(1 for r in survey if r["family"] == k and not r["implemented"])}
        for k, v in site.families.items()
    ]
    families.sort(key=lambda f: f["order"])
    return {"canonical_probe": canonical, "models": rows, "families": families,
            "survey": survey,
            "n_survey": len(survey),
            "n_field": sum(1 for r in survey if not r["implemented"])}


def build_results(site, cells) -> dict[str, Any]:
    agg = {(r["dataset"], r["model"], r["metric"]): r for r in site.metric_rows}
    by_cell = {(c["model"], c["task"]): c for c in cells}
    # (model, task, metric) -> published row. Keyed by metric, not just by the task's
    # primary one: the ECG literature reports macro-AUC where this site ranks on macro-F1,
    # so a lookup restricted to the primary metric can record almost nothing.
    reported = {
        (str(r.get("model")), str(r.get("task")), str(r.get("metric"))): r
        for r in (site.reported or [])
    }

    out: dict[str, Any] = {}
    for tid, task in sorted(site.tasks.items(), key=lambda kv: kv[1].get("order", 999)):
        ds = str(task.get("registry_dataset"))
        vocab = metric_vocabulary(site, str(task.get("label_mode")))
        # Column order: the primary metric first, then the rest of the vocabulary carried by
        # this snapshot OR by a published value. A metric in the vocabulary but absent from
        # both still gets no column. Reported metrics have to be unioned in: a task whose
        # snapshot holds no rows at all (LTAFDB) would otherwise offer no column for a
        # published number to land in, and the row would render as a status with no value.
        present = {m for (d, _mm, m) in agg if d == ds}
        present |= {m for (_mo, t, m) in reported if t == tid}
        cols = [task.get("primary_metric")] + sorted(
            (vocab & present) - {task.get("primary_metric")}
        )
        cols = [c for c in cols if c]

        # Registered models always get a row. Survey architectures appear only on the tasks
        # a paper actually cites them for -- see build_cells for why they are not
        # materialised against the whole grid.
        field_by_slug = {str(e.get("slug")): e for e in (site.field or [])}
        survey_here = sorted({
            mo for (mo, t, _m) in reported if t == tid and mo in field_by_slug
        })

        rows = []
        for name in sorted(site.registry.get("models", {})) + survey_here:
            is_survey = name in field_by_slug
            ed = field_by_slug[name] if is_survey else site.models.get(name, {})
            cell = by_cell.get((name, tid), {})
            metrics: dict[str, Any] = {}
            for m in cols:
                r = agg.get((ds, name, m))
                spec = site.metrics.get(m, {})
                if r is None:
                    # No measurement. A published value may fill the gap -- and only here,
                    # because a measurement is always produced under the protocol the rest
                    # of the table is comparable with, and must win.
                    rep = reported.get((name, tid, m))
                    rv = to_float(rep.get("value")) if rep else None
                    prec = spec.get("precision", 3)
                    metrics[m] = {
                        # Status is PER METRIC, not per row. A model can hold a published
                        # AUROC and no F1 at all, and the F1 cell must keep saying "not run"
                        # rather than borrowing the amber of the column beside it.
                        "status": "reported" if rv is not None
                                  else cell.get("status", "not_run"),
                        "value": rv,
                        "display": "--" if rv is None else f"{rv:.{prec}f}",
                        "sd": None, "sd_display": "--",
                        "n": (to_int(rep.get("n")) or 0) if rep else 0,
                        "averaging": None,
                        "direction": spec.get("direction", "none"),
                        "lower_ci": None, "upper_ci": None, "interval_display": "--",
                        "precision": prec,
                    }
                else:
                    val = to_float(r.get("mean"))
                    sdv = to_float(r.get("std"))
                    prec = spec.get("precision", 3)
                    metrics[m] = {
                        "status": cell.get("status"),
                        "value": val,
                        "display": fmt(val, prec),
                        "sd_display": fmt(sdv, prec) if sdv is not None else "--",
                        "sd": to_float(r.get("std")),
                        "n": to_int(r.get("n")) or 0,
                        "lower_ci": to_float(r.get("lower_ci")),
                        "upper_ci": to_float(r.get("upper_ci")),
                        "interval_display": (
                            f"[{to_float(r.get('lower_ci')):.{prec}f}, "
                            f"{to_float(r.get('upper_ci')):.{prec}f}]"
                            if to_float(r.get("lower_ci")) is not None
                            and to_float(r.get("upper_ci")) is not None
                            else "--"
                        ),
                        "averaging": r.get("averaging") or "unknown",
                        "direction": spec.get("direction", "none"),
                        "precision": spec.get("precision", 3),
                    }
            # `has_data` means MEASURED here, and gates ranking, the bars chart and
            # `rankable`. A published value must never raise it: ranking someone else's
            # number against ours would be the false comparison the amber bucket exists to
            # prevent. `is_reported` carries it instead, so the table can still show it.
            is_reported = any(v["status"] == "reported" for v in metrics.values())
            has_any = any(
                v["value"] is not None and v["status"] != "reported"
                for v in metrics.values()
            )
            rep_row = next(
                (reported[(name, tid, m)] for m in cols if (name, tid, m) in reported), None
            )
            src = (rep_row or {}).get("source") or {}
            reason = cell.get("reason")
            if is_reported and not has_any:
                note = str((rep_row or {}).get("protocol_note") or "").strip()
                reason = "Reported by the original authors, not measured here."
                reason += f" {note}" if note else ""
            rows.append({
                "model": name,
                "title": ed.get("title", name),
                "family": ed.get("family"),
                # Survey rows have no /models/<slug>/ page to link to, and the template must
                # not emit a link that 404s.
                "is_survey": is_survey,
                # A row carrying only published values reads as reported, so its chip
                # matches the colour of the number beside it.
                "status": "reported" if (is_reported and not has_any)
                          else cell.get("status"),
                "flags": cell.get("flags", []),
                "reason": reason,
                "has_data": has_any,
                "is_reported": is_reported,
                # Present on every row, empty where absent: strict_variables makes a missing
                # key a build error even on a hash the template never reaches.
                "reported_paper": str(src.get("paper_title") or ""),
                "reported_doi": str(src.get("doi") or ""),
                "protocol_note": str((rep_row or {}).get("protocol_note") or ""),
                "metrics": metrics,
            })

        primary = task.get("primary_metric")
        direction = (site.metrics.get(primary) or {}).get("direction", "higher")
        # Sort only in the metric's own direction, and only among rows that have a value.
        # A descending sort applied to a lower-is-better metric silently inverts the table.
        withdata = [r for r in rows if r["has_data"]]
        withdata.sort(
            key=lambda r: (r["metrics"][primary]["value"] if r["metrics"][primary]["value"] is not None else 0),
            reverse=(direction != "lower"),
        )
        # Three blocks, not two: measured (ranked), then published (alphabetical, never
        # ranked), then nothing at all. Sorting the reported rows by value would imply they
        # sit on the same scale as the measured ones, which is exactly what they do not.
        repdata = [r for r in rows if r["is_reported"] and not r["has_data"]]
        repdata.sort(key=lambda r: r["title"].lower())
        nodata = [r for r in rows if not r["has_data"] and not r["is_reported"]]
        nodata.sort(key=lambda r: r["title"].lower())

        out[tid] = {
            "id": tid,
            "title": task.get("title"),
            "short_title": task.get("short_title"),
            "primary_metric": primary,
            "direction": direction,
            "columns": cols,
            "label_mode": task.get("label_mode"),
            "expected_averaging": task.get("expected_averaging"),
            "expected_replicates": task.get("expected_replicates"),
            "replicate_kind": task.get("replicate_kind"),
            "scope": task.get("scope"),
            "in_journal": task.get("in_journal"),
            "n_with_data": len(withdata),
            "n_reported": len(repdata),
            "n_models": len(rows),
            # Split, not filtered. A results table listing every architecture that was never
            # trained is mostly em dashes -- on LTAFDB it was 21 rows of nothing at all, and
            # across the site 76 of 113 rows carried no value in any column. "Never trained"
            # is one sentence, not fifteen rows wide. The rows are still emitted and still
            # rendered, just behind a disclosure, so the journal's rule that no cell may be
            # left blank still holds and /coverage/ remains the full enumeration.
            "rows": withdata + repdata,
            "rows_no_data": nodata,
            "n_no_data": len(nodata),
            "rankable": all(
                (r["metrics"][primary]["n"] or 0) >= 3 for r in withdata
            ) and len(withdata) > 1,
        }
    return out


def build_coverage(site, cells) -> dict[str, Any]:
    # Seeded with every declared status at zero. A status that happens not to occur must
    # still render its legend entry and its count, and under strict_variables a missing key
    # is a build error rather than a blank.
    # The coverage universe is the models this site can actually run: registry x tasks.
    # Survey cells exist only where a paper was cited, so counting them here would let
    # adding a citation change a percentage that describes what was MEASURED -- and would
    # make the denominator grow every time someone reads a paper.
    grid = [c for c in cells if not c["is_survey"]]
    survey = [c for c in cells if c["is_survey"]]

    counts: dict[str, int] = {k: 0 for k in site.statuses}
    for c in grid:
        counts[c["status"]] = counts.get(c["status"], 0) + 1
    shows = {k for k, v in site.statuses.items() if v.get("shows_number")}
    # Coverage means what THIS SITE measured. A value published by the original authors shows
    # a number but was produced under someone else's protocol, so it is counted separately
    # rather than folded into the coverage percentage it did not earn.
    kit_statuses = {k for k, v in site.statuses.items() if v.get("bucket") == "kit"}
    with_number = sum(v for k, v in counts.items() if k in shows and k in kit_statuses)
    with_reported = sum(v for k, v in counts.items()
                        if site.statuses.get(k, {}).get("bucket") == "reported")
    ns = sorted(c["n"] for c in grid if c["n"])
    median_n = ns[len(ns) // 2] if ns else 0
    tasks_with_data = sorted({c["task"] for c in grid if c["n"]})
    models_with_data = sorted({c["model"] for c in grid if c["n"]})
    status_summary = [
        {"key": k, "label": v.get("label", k), "glyph": v.get("glyph", ""),
         "blurb": v.get("blurb", ""), "shows_number": bool(v.get("shows_number")),
         "bucket": v.get("bucket", ""), "count": counts.get(k, 0)}
        for k, v in site.statuses.items()
    ]
    # What the legend renders. Nine statuses is not a legend; three buckets is. Each carries
    # the statuses it absorbs so a reader can still find out what the glyphs mean.
    bucket_summary = [
        {"key": bk,
         "label": bv.get("label", bk),
         "glyph": bv.get("glyph", ""),
         "blurb": bv.get("blurb", ""),
         "order": bv.get("order", 999),
         "count": sum(counts.get(k, 0) for k, v in site.statuses.items()
                      if v.get("bucket") == bk),
         "statuses": [
             {"key": k, "label": v.get("label", k), "glyph": v.get("glyph", ""),
              "blurb": v.get("blurb", ""), "count": counts.get(k, 0)}
             for k, v in site.statuses.items() if v.get("bucket") == bk
         ]}
        for bk, bv in site.buckets.items()
    ]
    bucket_summary.sort(key=lambda b: b["order"])
    return {
        "cells": cells,
        "counts": counts,
        "status_summary": status_summary,
        "bucket_summary": bucket_summary,
        "total": len(grid),
        "with_number": with_number,
        "with_reported": with_reported,
        "pct_with_number": round(100.0 * with_number / len(grid), 1) if grid else 0.0,
        "median_replicates": median_n,
        "tasks_with_data": tasks_with_data,
        "models_with_data": models_with_data,
        "n_models": len(site.registry.get("models", {})),
        "n_tasks": len(site.tasks),
        # Survey architectures cited on a task. Counted and listed separately from the grid
        # above, never folded into it: these are other people's numbers for models this site
        # does not implement, so they say nothing about this site's coverage.
        "survey_cells": survey,
        "n_survey_cells": len(survey),
        "n_survey_models": len({c["model"] for c in survey}),
    }


PLOT_CAPTIONS = {
    "confusion-matrix": "Confusion matrix on the test split.",
    "calibration-curve": "Reliability diagram: predicted confidence against observed accuracy.",
    "loss-curve": "Training and validation loss per epoch.",
    "accuracy-curve": "Training and validation accuracy per epoch.",
}
PLOT_ORDER = list(PLOT_CAPTIONS)


def build_plots(site, cells) -> dict[str, Any]:
    """Index the committed run plots by scanning assets/runs/.

    Derived from what is on disk rather than from a written manifest, so the index cannot
    reference a PNG that was never committed -- which under strict_variables would be a
    build error, and in a browser a broken image. CI has no access to the raw run
    directories, so scanning is also the only thing it *can* do.
    """
    root = ROOT / "assets" / "runs"
    # TOTAL over the whole cell universe: every cell gets a key, empty where there are no
    # plots. strict_variables makes a missing key a build error, and the alternative --
    # guarding every lookup in the template -- puts the invariant somewhere it can be
    # forgotten.
    out: dict[str, list[dict[str, Any]]] = {f"{c['task']}|{c['model']}": [] for c in cells}
    if not root.is_dir():
        return out
    for task_dir in sorted(root.iterdir()):
        if not task_dir.is_dir():
            continue
        for model_dir in sorted(task_dir.iterdir()):
            if not model_dir.is_dir():
                continue
            entries = []
            for png in sorted(model_dir.glob("*.png")):
                kind = png.stem
                entries.append({
                    "kind": kind,
                    "label": kind.replace("-", " ").capitalize(),
                    "caption": PLOT_CAPTIONS.get(kind, ""),
                    "file": f"/assets/runs/{task_dir.name}/{model_dir.name}/{png.name}",
                })
            if entries:
                entries.sort(key=lambda e: PLOT_ORDER.index(e["kind"])
                             if e["kind"] in PLOT_ORDER else 99)
                out[f"{task_dir.name}|{model_dir.name}"] = entries
    return out


def build_evidence(site, coverage, results, catalogue) -> dict[str, Any]:
    manifest = site.manifest
    flags = manifest.get("schema_flags") or {}
    protocol = manifest.get("protocol") or {}
    rankable = [t for t, v in results.items() if v["rankable"]]
    return {
        "snapshot_id": site.snapshot_id,
        "snapshot_status": manifest.get("status"),
        "snapshot_label": manifest.get("label"),
        "generated_utc": manifest.get("generated_utc"),
        "kit_version": site.kit_version,
        "kit_git_sha": (manifest.get("produced_by") or {}).get("kit_git_sha"),
        "n_models": coverage["n_models"],
        "n_survey": catalogue["n_survey"],
        "n_field": catalogue["n_field"],
        "n_models_with_data": len(coverage["models_with_data"]),
        "n_tasks": coverage["n_tasks"],
        "n_tasks_with_data": len(coverage["tasks_with_data"]),
        "cells_total": coverage["total"],
        "cells_with_number": coverage["with_number"],
        "pct_with_number": coverage["pct_with_number"],
        "median_replicates": coverage["median_replicates"],
        "replicate_kind": protocol.get("replicate_kind"),
        "calibration_present": flags.get("calibration_metrics_present", False),
        "averaging_recorded": flags.get("average_column_present", False),
        "observed_averagings": flags.get("observed_averagings", []),
        "interval_kind": protocol.get("interval_kind"),
        "bootstrap_ci": protocol.get("bootstrap_ci"),
        "rankable_tasks": rankable,
        "any_rankable": bool(rankable),
        "min_seeds_for_interval": 3,
    }


# --------------------------------------------------------------------------------------
# Generated colour tokens (so no literal hex ever reaches an SVG or a template)
# --------------------------------------------------------------------------------------

def write_tokens(site) -> str:
    light, dark = [], []
    for key, spec in site.statuses.items():
        light.append(f"  --status-{key}: {spec['color_light']};")
        dark.append(f"  --status-{key}: {spec['color_dark']};")
    for key, spec in site.buckets.items():
        light.append(f"  --bucket-{key}: {spec['color_light']};")
        dark.append(f"  --bucket-{key}: {spec['color_dark']};")
    css = (
        "/* GENERATED by tools/build_site_data.py from _data/statuses.yml. Do not edit.\n"
        "   Status colours live in YAML so the swatch, the chip and the SVG cell cannot\n"
        "   disagree, and so a theme has to define both variants or the build fails. */\n"
        ':root, :root[data-theme="light"] {\n' + "\n".join(light) + "\n}\n"
        ':root[data-theme="dark"] {\n' + "\n".join(dark) + "\n}\n"
        "@media (prefers-color-scheme: dark) {\n"
        '  :root:not([data-theme="light"]) {\n'
        + "\n".join("  " + line for line in dark) + "\n  }\n}\n"
    )
    GEN_CSS.mkdir(parents=True, exist_ok=True)
    (GEN_CSS / "tokens.css").write_text(css, encoding="utf-8")
    return css


# --------------------------------------------------------------------------------------
# SVG charts
# --------------------------------------------------------------------------------------

def svg_coverage_matrix(site, cells) -> str:
    models = [m["registry_name"] for m in build_catalogue(site, cells)["models"]]
    titles = {m["registry_name"]: m["title"] for m in build_catalogue(site, cells)["models"]}
    tasks = sorted(site.tasks.items(), key=lambda kv: kv[1].get("order", 999))
    by = {(c["model"], c["task"]): c for c in cells}

    cw, ch, pad_l, pad_t = 104, 26, 168, 76
    w = pad_l + cw * len(tasks) + 16
    h = pad_t + ch * len(models) + 16

    out = [
        f'<svg class="chart chart-coverage" viewBox="0 0 {w} {h}" width="100%" '
        f'height="{h}" role="img" xmlns="http://www.w3.org/2000/svg" '
        f'aria-label="Coverage of {len(models)} architectures across {len(tasks)} tasks">'
    ]
    for j, (tid, t) in enumerate(tasks):
        x = pad_l + j * cw + cw / 2
        label = esc(t.get("short_title") or tid)
        out.append(
            f'<text x="{x:.0f}" y="{pad_t - 44}" class="chart-collabel" '
            f'text-anchor="middle" transform="rotate(-18 {x:.0f} {pad_t - 44})">{label}</text>'
        )
    for i, m in enumerate(models):
        y = pad_t + i * ch
        out.append(f'<text x="{pad_l - 12}" y="{y + 17}" class="chart-rowlabel" '
                   f'text-anchor="end">{esc(titles[m])}</text>')
        for j, (tid, t) in enumerate(tasks):
            c = by[(m, tid)]
            st = site.statuses[c["status"]]
            x = pad_l + j * cw
            tip = f'{titles[m]} on {t.get("short_title")}: {st["label"]}'
            if c["value"] is not None:
                tip += f' -- {c["metric"]} {fmt(c["value"])} (n={c["n"]})'
            if c["flags"]:
                tip += " -- " + ", ".join(f.replace("_", " ") for f in c["flags"])
            out.append(
                f'<g class="cov-cell cov-{c["status"]}"><title>{esc(tip)}</title>'
                f'<rect x="{x + 2}" y="{y + 2}" width="{cw - 6}" height="{ch - 5}" rx="4" '
                f'fill="var(--status-{c["status"]})" fill-opacity="0.16" '
                f'stroke="var(--status-{c["status"]})" stroke-opacity="0.5"/>'
                f'<text x="{x + cw / 2 - 2:.0f}" y="{y + 17}" text-anchor="middle" '
                f'class="cov-glyph" fill="var(--status-{c["status"]})">'
                f'{esc(fmt(c["value"]) if c["value"] is not None else st["glyph"])}</text>'
                f"</g>"
            )
    out.append("</svg>")
    return "\n".join(out)


def svg_task_bars(site, task_result) -> str:
    rows = [r for r in task_result["rows"] if r["has_data"]]
    primary = task_result["primary_metric"]
    if not rows:
        return ""
    bar_h, gap, pad_l, pad_t, pad_r = 26, 8, 150, 34, 56
    w = 720
    h = pad_t + len(rows) * (bar_h + gap) + 26
    plot_w = w - pad_l - pad_r
    vmax = max((r["metrics"][primary]["value"] or 0) for r in rows)
    vmax = max(vmax, 0.001)
    scale = 1.0 if vmax <= 1.0 else vmax

    out = [
        f'<svg class="chart chart-bars" viewBox="0 0 {w} {h}" width="100%" height="{h}" '
        f'role="img" xmlns="http://www.w3.org/2000/svg" '
        f'aria-label="{esc(primary)} by architecture on {esc(task_result["short_title"])}">'
    ]
    for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
        x = pad_l + frac * plot_w
        out.append(f'<line x1="{x:.1f}" y1="{pad_t - 8}" x2="{x:.1f}" y2="{h - 20}" '
                   f'stroke="var(--grid)" stroke-width="1"/>')
        out.append(f'<text x="{x:.1f}" y="{h - 6}" class="chart-tick" text-anchor="middle">'
                   f'{frac * scale:.2f}</text>')
    out.append(f'<text x="{pad_l}" y="{pad_t - 18}" class="chart-axislabel">'
               f'{esc(primary)} (higher is better)</text>')

    for i, r in enumerate(rows):
        m = r["metrics"][primary]
        y = pad_t + i * (bar_h + gap)
        val = m["value"] or 0
        bw = plot_w * (val / scale)
        status = r["status"]
        out.append(f'<text x="{pad_l - 10}" y="{y + 17}" class="chart-rowlabel" '
                   f'text-anchor="end">{esc(r["title"])}</text>')
        tip = f'{r["title"]}: {primary} {fmt(val)} (n={m["n"]}, averaging {m["averaging"]})'
        if r["flags"]:
            tip += " -- " + ", ".join(f.replace("_", " ") for f in r["flags"])
        out.append(f'<g class="bar bar-{status}"><title>{esc(tip)}</title>')
        out.append(f'<rect x="{pad_l}" y="{y + 3}" width="{max(bw, 1):.1f}" '
                   f'height="{bar_h - 6}" rx="3" fill="var(--status-{status})" '
                   f'fill-opacity="0.55" stroke="var(--status-{status})"/>')
        # Whisker: only drawn when a dispersion actually exists. At n=1 there is nothing
        # to draw, and drawing a zero-width whisker would imply a precision we do not have.
        sd = m.get("sd")
        if sd:
            lo = plot_w * max(0.0, (val - sd) / scale)
            hi = plot_w * min(1.0, (val + sd) / scale)
            yc = y + bar_h / 2
            out.append(f'<line x1="{pad_l + lo:.1f}" y1="{yc:.1f}" x2="{pad_l + hi:.1f}" '
                       f'y2="{yc:.1f}" stroke="currentColor" stroke-width="1.5"/>')
        out.append(f'<text x="{pad_l + max(bw, 1) + 8:.1f}" y="{y + 17}" '
                   f'class="chart-value">{fmt(val)}'
                   f'{" &#177; --" if not sd else ""}</text>')
        out.append("</g>")
    out.append("</svg>")
    return "\n".join(out)



# --------------------------------------------------------------------------------------
# Statistics charts. Same rules as every other chart: emitted from the validated JSON,
# every colour a custom property, inlined by Liquid, no JavaScript.
# --------------------------------------------------------------------------------------

def _hbar_frame(n_rows: int, w: int = 720, bar_h: int = 22, gap: int = 7,
                pad_l: int = 190, pad_t: int = 12, pad_r: int = 56):
    h = pad_t + n_rows * (bar_h + gap) + 10
    return w, h, bar_h, gap, pad_l, pad_t, w - pad_l - pad_r


def svg_stacked_counts(items: list[tuple[str, int, int]], aria: str) -> str:
    """Horizontal bars split into implemented (filled) and field-survey (outline) segments."""
    if not items:
        return ""
    w, h, bar_h, gap, pad_l, pad_t, plot_w = _hbar_frame(len(items))
    vmax = max((a + b) for _, a, b in items) or 1
    out = [f'<svg class="chart" viewBox="0 0 {w} {h}" width="100%" height="{h}" role="img" '
           f'xmlns="http://www.w3.org/2000/svg" aria-label="{esc(aria)}">']
    for i, (label, impl, field) in enumerate(items):
        y = pad_t + i * (bar_h + gap)
        wi = plot_w * impl / vmax
        wf = plot_w * field / vmax
        out.append(f'<text x="{pad_l - 10}" y="{y + 15}" class="chart-rowlabel" '
                   f'text-anchor="end">{esc(label)}</text>')
        tip = f"{label}: {impl} implemented, {field} field survey"
        out.append(f'<g><title>{esc(tip)}</title>')
        if impl:
            out.append(f'<rect x="{pad_l}" y="{y + 2}" width="{max(wi, 1):.1f}" '
                       f'height="{bar_h - 4}" fill="var(--text)" fill-opacity="0.65"/>')
        if field:
            out.append(f'<rect x="{pad_l + wi:.1f}" y="{y + 2}" width="{max(wf, 1):.1f}" '
                       f'height="{bar_h - 4}" fill="none" stroke="var(--muted)" '
                       f'stroke-width="1.2"/>')
        out.append(f'<text x="{pad_l + wi + wf + 8:.1f}" y="{y + 15}" class="chart-value">'
                   f'{impl + field}</text>')
        out.append("</g>")
    out.append("</svg>")
    return "\n".join(out)


def svg_params_log(rows: list[dict[str, Any]]) -> str:
    """Measured parameter counts on a log scale. Kit models only: nothing here is reported."""
    import math

    rows = [r for r in rows if r.get("params_m")]
    rows.sort(key=lambda r: r["params_m"], reverse=True)
    if not rows:
        return ""
    w, h, bar_h, gap, pad_l, pad_t, plot_w = _hbar_frame(len(rows), bar_h=18, gap=6, pad_t=30)
    h += 20
    lo, hi = 0.05, 10.0
    def x_of(v: float) -> float:
        f = (math.log10(v) - math.log10(lo)) / (math.log10(hi) - math.log10(lo))
        return pad_l + plot_w * max(0.0, min(1.0, f))
    out = [f'<svg class="chart" viewBox="0 0 {w} {h}" width="100%" height="{h}" role="img" '
           f'xmlns="http://www.w3.org/2000/svg" '
           f'aria-label="Measured parameter counts of the implemented architectures, log scale">']
    for tick in (0.1, 0.3, 1.0, 3.0, 10.0):
        x = x_of(tick)
        out.append(f'<line x1="{x:.1f}" y1="{pad_t - 6}" x2="{x:.1f}" y2="{h - 24}" '
                   f'stroke="var(--grid)" stroke-width="1"/>')
        out.append(f'<text x="{x:.1f}" y="{h - 10}" class="chart-tick" '
                   f'text-anchor="middle">{tick:g}M</text>')
    out.append(f'<text x="{pad_l}" y="{pad_t - 14}" class="chart-axislabel">parameters '
               f'(millions, log scale)</text>')
    for i, r in enumerate(rows):
        y = pad_t + i * (bar_h + gap)
        bw = x_of(r["params_m"]) - pad_l
        out.append(f'<g><title>{esc(r["title"])}: {r["params_m"]}M parameters</title>')
        out.append(f'<text x="{pad_l - 10}" y="{y + 13}" class="chart-rowlabel" '
                   f'text-anchor="end">{esc(r["title"])}</text>')
        out.append(f'<rect x="{pad_l}" y="{y + 2}" width="{max(bw, 1):.1f}" '
                   f'height="{bar_h - 4}" fill="var(--muted)" fill-opacity="0.45"/>')
        out.append(f'<text x="{pad_l + max(bw, 1) + 8:.1f}" y="{y + 13}" class="chart-value">'
                   f'{r["params_m"]}</text>')
        out.append("</g>")
    out.append("</svg>")
    return "\n".join(out)


def svg_status_counts(site, coverage) -> str:
    items = [(v["label"], v["key"], v["count"]) for v in coverage["status_summary"] if v["count"]]
    if not items:
        return ""
    w, h, bar_h, gap, pad_l, pad_t, plot_w = _hbar_frame(len(items))
    vmax = max(n for _, _, n in items) or 1
    out = [f'<svg class="chart" viewBox="0 0 {w} {h}" width="100%" height="{h}" role="img" '
           f'xmlns="http://www.w3.org/2000/svg" '
           f'aria-label="Model by task cells by status in the current snapshot">']
    for i, (label, key, n) in enumerate(items):
        y = pad_t + i * (bar_h + gap)
        bw = plot_w * n / vmax
        out.append(f'<g><title>{esc(label)}: {n} cells</title>')
        out.append(f'<text x="{pad_l - 10}" y="{y + 15}" class="chart-rowlabel" '
                   f'text-anchor="end">{esc(label)}</text>')
        out.append(f'<rect x="{pad_l}" y="{y + 2}" width="{max(bw, 1):.1f}" height="{bar_h - 4}" '
                   f'fill="var(--status-{key})" fill-opacity="0.5" '
                   f'stroke="var(--status-{key})" stroke-opacity="0.6"/>')
        out.append(f'<text x="{pad_l + max(bw, 1) + 8:.1f}" y="{y + 15}" class="chart-value">{n}</text>')
        out.append("</g>")
    out.append("</svg>")
    return "\n".join(out)


def build_stats_charts(site, catalogue, coverage) -> dict[str, str]:
    survey = catalogue["survey"]
    fam_items = [(f["label"], f["count_implemented"], f["count_field"])
                 for f in catalogue["families"] if f["count"]]
    years = sorted({r["year"] for r in survey if r["year"]})
    year_items = []
    if years:
        for y in range(min(years), max(years) + 1):
            impl = sum(1 for r in survey if r["year"] == y and r["implemented"])
            fld = sum(1 for r in survey if r["year"] == y and not r["implemented"])
            year_items.append((str(y), impl, fld))
    return {
        "stats_family": svg_stacked_counts(
            fam_items, "Catalogued architectures by family, implemented versus field survey"),
        "stats_year": svg_stacked_counts(
            year_items, "Catalogued architectures by publication year"),
        "stats_params": svg_params_log(catalogue["models"] and [
            {"title": m["title"], "params_m": m["params_m"]} for m in catalogue["models"]]),
        "stats_status": svg_status_counts(site, coverage),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--strict", action="store_true", default=True)
    ap.parse_args(argv)

    site = load_site()
    cells, problems = build_cells(site)
    if problems:
        for p in problems:
            print(f"  {p}")
        raise BuildError(f"{len(problems)} problem(s) building the cell universe.")

    catalogue = build_catalogue(site, cells)
    results = build_results(site, cells)
    coverage = build_coverage(site, cells)
    evidence = build_evidence(site, coverage, results, catalogue)
    plots = build_plots(site, cells)

    GEN_DATA.mkdir(parents=True, exist_ok=True)
    GEN_SVG.mkdir(parents=True, exist_ok=True)
    for name, payload in (
        ("catalogue", catalogue), ("results", results),
        ("coverage", coverage), ("evidence", evidence), ("plots", plots),
        ("manifest", site.manifest),
    ):
        (GEN_DATA / f"{name}.json").write_text(
            json.dumps(payload, indent=1, default=str) + "\n", encoding="utf-8"
        )

    write_tokens(site)

    # Charts are emitted as SVG markup into a data file and printed with {{ }} rather than
    # pulled in with a dynamic {% include %}. Two reasons: Jekyll's variable-include form is
    # fragile, and every task needs a key whether or not it has a chart (strict_variables).
    # Liquid does not auto-escape, so the markup lands inline in the HTML -- which is the
    # property that matters: an <img src> SVG is an isolated document that sees neither the
    # stylesheet nor :root[data-theme], so currentColor would resolve to black.
    charts: dict[str, str] = {"coverage_matrix": svg_coverage_matrix(site, cells)}
    charts.update(build_stats_charts(site, catalogue, coverage))
    for tid, tr in results.items():
        charts[f"bars_{tid.replace('-', '_')}"] = svg_task_bars(site, tr)
    (GEN_DATA / "charts.json").write_text(
        json.dumps(charts, indent=1) + "\n", encoding="utf-8"
    )
    # Also written to disk for inspection and diffing; not consumed by the templates.
    for name, markup in charts.items():
        if markup:
            (GEN_SVG / f"{name}.svg").write_text(markup, encoding="utf-8")
    n_charts = sum(1 for v in charts.values() if v)

    print(f"generated {len(list(GEN_DATA.glob('*.json')))} data files, {n_charts} charts")
    print(f"  snapshot        {site.snapshot_id} ({site.manifest.get('status')})")
    print(f"  cells           {coverage['total']} "
          f"({coverage['with_number']} with a number, {coverage['pct_with_number']}%)")
    print(f"  statuses        {coverage['counts']}")
    print(f"  rankable tasks  {evidence['rankable_tasks'] or 'none'}")
    print(f"  run plots       {sum(len(v) for v in plots.values())} across {len(plots)} cells")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
