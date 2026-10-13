"""Provoke every gate deliberately.

A validator nobody has ever seen fail is decorative. These tests corrupt a throwaway copy
of the repo in each of the ways the real data can go wrong, and assert the specific error
code fires. They are the reason to believe `make validate` means anything.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
COPY_ITEMS = ["_models", "_tasks", "_data", "results", "tools"]


def _rehash(snapshot: Path) -> None:
    """Rewrite CHECKSUMS so a test can target a gate other than E_CHECKSUM."""
    lines = []
    for f in sorted(snapshot.iterdir()):
        if f.name == "CHECKSUMS.sha256" or not f.is_file():
            continue
        h = hashlib.sha256()
        h.update(f.read_bytes())
        lines.append(f"{h.hexdigest()}  {f.name}")
    (snapshot / "CHECKSUMS.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


@pytest.fixture
def sandbox(tmp_path: Path) -> Path:
    for item in COPY_ITEMS:
        src = REPO / item
        if src.is_dir():
            shutil.copytree(src, tmp_path / item, ignore=shutil.ignore_patterns("__pycache__"))
    (tmp_path / "_data" / "generated").mkdir(parents=True, exist_ok=True)
    return tmp_path


def run_validate(root: Path) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, str(root / "tools" / "validate.py"), "--strict"],
        capture_output=True, text=True, cwd=root,
    )
    return proc.returncode, proc.stdout + proc.stderr


def snapshot_dir(root: Path) -> Path:
    import yaml
    cur = yaml.safe_load((root / "_data" / "snapshots.yml").read_text())["current"]
    return root / "results" / "snapshots" / str(cur)


def test_clean_repo_passes(sandbox: Path) -> None:
    rc, out = run_validate(sandbox)
    assert rc == 0, out


def test_missing_model_page(sandbox: Path) -> None:
    (sandbox / "_models" / "tcn.md").unlink()
    rc, out = run_validate(sandbox)
    assert rc == 1 and "E_MISSING_PAGE" in out and "tcn" in out


def test_orphan_model_page(sandbox: Path) -> None:
    (sandbox / "_models" / "not-a-model.md").write_text(
        "---\nregistry_name: not-a-model\ntitle: X\nfamily: cnn\nmaturity: experimental\n"
        "one_liner: x\napplicability: {gradient_attribution: true, occlusion: true, "
        "class_activation: false}\n---\n", encoding="utf-8")
    rc, out = run_validate(sandbox)
    assert rc == 1 and "E_ORPHAN_PAGE" in out


def test_forbidden_key(sandbox: Path) -> None:
    p = sandbox / "_models" / "resnet.md"
    p.write_text(p.read_text().replace("maturity: reference",
                                       "maturity: reference\nparams_total: 999", 1))
    rc, out = run_validate(sandbox)
    assert rc == 1 and "E_FORBIDDEN_KEY" in out and "params_total" in out


def test_stem_mismatch(sandbox: Path) -> None:
    p = sandbox / "_models" / "resnet.md"
    p.write_text(p.read_text().replace("registry_name: resnet", "registry_name: resnet-wang", 1))
    rc, out = run_validate(sandbox)
    assert rc == 1 and "E_STEM_MISMATCH" in out


def test_unknown_family(sandbox: Path) -> None:
    p = sandbox / "_models" / "resnet.md"
    p.write_text(p.read_text().replace("family: cnn", "family: quantum", 1))
    rc, out = run_validate(sandbox)
    assert rc == 1 and "E_UNKNOWN_FAMILY" in out


def test_cam_claim_rejected(sandbox: Path) -> None:
    """The site must not claim a capability deepecgkit does not implement."""
    p = sandbox / "_models" / "resnet.md"
    p.write_text(p.read_text().replace("class_activation: false", "class_activation: true", 1))
    rc, out = run_validate(sandbox)
    assert rc == 1 and "E_CAM_CLAIM" in out


def test_checksum_mismatch(sandbox: Path) -> None:
    f = snapshot_dir(sandbox) / "seed_metrics_long.csv"
    f.write_text(f.read_text().replace("0.7539912227743227", "0.9999999999999999", 1))
    rc, out = run_validate(sandbox)
    assert rc == 1 and "E_CHECKSUM" in out


def test_mixed_averaging_in_one_column(sandbox: Path) -> None:
    """reconcile_averaging groups by (dataset, model) and cannot see this."""
    snap = snapshot_dir(sandbox)
    f = snap / "seed_metrics_long.csv"
    rows = f.read_text().splitlines()
    for i, r in enumerate(rows):
        if r.startswith("af-classification,resnet,f1,unknown"):
            rows[i] = r.replace(",unknown,", ",macro,", 1)
            break
    else:
        pytest.skip("no af-classification f1 row to perturb")
    f.write_text("\n".join(rows) + "\n")
    _rehash(snap)
    rc, out = run_validate(sandbox)
    assert rc == 1 and "E_MIXED_AVERAGING" in out


def test_unknown_metric_in_snapshot(sandbox: Path) -> None:
    snap = snapshot_dir(sandbox)
    f = snap / "seed_metrics_long.csv"
    rows = f.read_text().splitlines()
    rows.append("af-classification,resnet,made_up_metric,unknown,1,1,0.5,,,,,-1")
    f.write_text("\n".join(rows) + "\n")
    _rehash(snap)
    rc, out = run_validate(sandbox)
    assert rc == 1 and "E_UNKNOWN_METRIC" in out


def test_status_missing_dark_colour(sandbox: Path) -> None:
    """A single colour cannot survive the theme toggle, so both are mandatory."""
    p = sandbox / "_data" / "statuses.yml"
    p.write_text(p.read_text().replace('  color_dark: "#22c55e"\n', "", 1))
    rc, out = run_validate(sandbox)
    assert rc == 1 and "E_STATUS_FIELD" in out


def test_metric_direction_must_match_library(sandbox: Path) -> None:
    """Flipping ECE to higher-is-better would invert the calibration ranking."""
    p = sandbox / "_data" / "metrics.yml"
    p.write_text(p.read_text().replace(
        'ece:                    { label: "ECE",         direction: lower',
        'ece:                    { label: "ECE",         direction: higher', 1))
    rc, out = run_validate(sandbox)
    assert rc == 1 and "E_DIRECTION" in out


def test_two_tasks_cannot_share_a_dataset(sandbox: Path) -> None:
    """A metrics CSV records only `dataset`, so its rows would be unattributable."""
    src = (sandbox / "_tasks" / "ptbxl-multilabel.md").read_text()
    (sandbox / "_tasks" / "ptbxl-duplicate.md").write_text(
        src.replace("id: ptbxl-multilabel", "id: ptbxl-duplicate", 1), encoding="utf-8")
    rc, out = run_validate(sandbox)
    assert rc == 1 and "E_AMBIGUOUS_DATASET" in out


def test_legacy_runs_cannot_be_declared_current(sandbox: Path) -> None:
    p = snapshot_dir(sandbox) / "manifest.yml"
    p.write_text(p.read_text().replace("status: preliminary", "status: current", 1))
    _rehash(snapshot_dir(sandbox))
    rc, out = run_validate(sandbox)
    assert rc == 1 and "E_LEGACY_STATUS" in out


def test_field_entry_colliding_with_registry(sandbox: Path) -> None:
    """A survey entry for an implemented model is stale by definition."""
    p = sandbox / "_data" / "field.yml"
    p.write_text(p.read_text() + """
- slug: resnet
  title: "Duplicate ResNet"
  family: cnn
  one_liner: "x"
  params_m_reported: null
  search_keywords: ""
  origin: {paper_title: "X", authors: null, venue: "Y", year: 2020, doi: null,
           code_url: null, adapted_from: null}
""", encoding="utf-8")
    rc, out = run_validate(sandbox)
    assert rc == 1 and "E_FIELD_IMPLEMENTED" in out and "resnet" in out


def test_field_entry_with_measured_fact(sandbox: Path) -> None:
    """Nothing about an unimplemented model is measured by this site."""
    p = sandbox / "_data" / "field.yml"
    p.write_text(p.read_text().replace(
        "- slug: clocs\n  title: \"CLOCS\"",
        "- slug: clocs\n  params_total: 999\n  title: \"CLOCS\"", 1), encoding="utf-8")
    rc, out = run_validate(sandbox)
    assert rc == 1 and "E_FIELD_FORBIDDEN" in out and "params_total" in out


# ── Legend buckets and paper-reported values ──────────────────────────────────────────
# _data/reported.yml carries someone else's numbers. Every gate below exists because a
# wrong row would put a published value into a table that reads as this site's own runs.

def _write_reported(root: Path, body: str) -> None:
    (root / "_data" / "reported.yml").write_text(body, encoding="utf-8")


REPORTED_OK = """
- model: afmodel
  task: ptbxl-multilabel
  metric: f1
  value: 0.812
  n: null
  source:
    paper_title: "A paper"
    doi: "10.1000/example"
  protocol_note: "Authors' own split."
"""


def test_reported_fills_an_unmeasured_cell(sandbox: Path) -> None:
    """The mechanism end to end: a published value takes the `reported` status."""
    _write_reported(sandbox, REPORTED_OK)
    rc, out = run_validate(sandbox)
    assert rc == 0, out

    sys.path.insert(0, str(sandbox / "tools"))
    try:
        for mod in ("common", "build_site_data"):
            sys.modules.pop(mod, None)
        import common
        site = common.load_site(sandbox)
        cells = {(c["model"], c["task"]): c for c in common.build_cells(site)[0]}
    finally:
        sys.path.remove(str(sandbox / "tools"))
        for mod in ("common", "build_site_data"):
            sys.modules.pop(mod, None)

    cell = cells[("afmodel", "ptbxl-multilabel")]
    assert cell["status"] == "reported"
    assert cell["value"] == 0.812
    assert cell["display"] == "0.812"
    assert cell["reported_doi"] == "10.1000/example"
    assert "not measured here" in cell["reason"]


def test_reported_never_overrides_a_measurement(sandbox: Path) -> None:
    """A measured pair must win, and the dead row must be reported rather than ignored."""
    _write_reported(sandbox, REPORTED_OK.replace("afmodel", "convnext-v2"))
    rc, out = run_validate(sandbox)
    assert rc == 1 and "E_REPORTED_SHADOWED" in out


def test_reported_unknown_model(sandbox: Path) -> None:
    _write_reported(sandbox, REPORTED_OK.replace("model: afmodel", "model: no-such-model"))
    rc, out = run_validate(sandbox)
    assert rc == 1 and "E_REPORTED_MODEL" in out


def test_reported_unknown_task(sandbox: Path) -> None:
    _write_reported(sandbox, REPORTED_OK.replace("ptbxl-multilabel", "no-such-task"))
    rc, out = run_validate(sandbox)
    assert rc == 1 and "E_REPORTED_TASK" in out


def test_reported_metric_undefined_for_label_mode(sandbox: Path) -> None:
    """mcc is single-label only; claiming it on a multi-label task invents a number."""
    _write_reported(sandbox, REPORTED_OK.replace("metric: f1", "metric: mcc"))
    rc, out = run_validate(sandbox)
    assert rc == 1 and "E_REPORTED_METRIC" in out


def test_reported_without_a_source(sandbox: Path) -> None:
    body = REPORTED_OK.replace('    paper_title: "A paper"\n', "").replace(
        '    doi: "10.1000/example"\n', "")
    _write_reported(sandbox, body.replace("  source:\n", "  source: {}\n"))
    rc, out = run_validate(sandbox)
    assert rc == 1 and "E_REPORTED_SOURCE" in out


def test_reported_duplicate_pair(sandbox: Path) -> None:
    _write_reported(sandbox, REPORTED_OK + REPORTED_OK)
    rc, out = run_validate(sandbox)
    assert rc == 1 and "E_REPORTED_DUPLICATE" in out


REPORTED_SURVEY = """
- model: clocs
  task: ptbxl-multilabel
  metric: auroc
  value: 0.912
  n: null
  source:
    paper_title: "A paper"
    doi: "10.1000/example"
  protocol_note: "Authors' own split."
"""


def test_reported_survey_model_gets_a_cell(sandbox: Path) -> None:
    """A _data/field.yml architecture may hold a published result cell."""
    _write_reported(sandbox, REPORTED_SURVEY)
    rc, out = run_validate(sandbox)
    assert rc == 0, out
    _site, cells, results = _build(sandbox)

    cell = next(c for c in cells if c["model"] == "clocs" and c["task"] == "ptbxl-multilabel")
    assert cell["is_survey"] is True
    assert cell["status"] == "reported"
    assert cell["value"] == 0.912
    # The cell takes the metric the PAPER reports, not the task's primary metric: a survey
    # row carrying an empty macro-F1 would say nothing at all.
    assert cell["metric"] == "auroc"
    assert cell["reported_doi"] == "10.1000/example"
    assert "Not implemented in DeepECG-Kit" in cell["reason"]

    row = next(x for x in results["ptbxl-multilabel"]["rows"] if x["model"] == "clocs")
    assert row["is_survey"] is True, "the template needs this to avoid linking a 404"
    assert row["has_data"] is False
    assert row["metrics"]["auroc"]["display"] == "0.912"


def test_survey_cells_stay_out_of_the_coverage_denominator(sandbox: Path) -> None:
    """Citing a paper must not move a percentage describing what this site MEASURED."""
    sys.path.insert(0, str(sandbox / "tools"))
    try:
        for mod in ("common", "build_site_data"):
            sys.modules.pop(mod, None)
        import build_site_data
        import common
        before = build_site_data.build_coverage(
            common.load_site(sandbox), common.build_cells(common.load_site(sandbox))[0])
        _write_reported(sandbox, REPORTED_SURVEY)
        site = common.load_site(sandbox)
        after = build_site_data.build_coverage(site, common.build_cells(site)[0])
    finally:
        sys.path.remove(str(sandbox / "tools"))
        for mod in ("common", "build_site_data"):
            sys.modules.pop(mod, None)

    assert after["total"] == before["total"], "the grid is registry x tasks and must not grow"
    assert after["pct_with_number"] == before["pct_with_number"]
    assert after["n_survey_cells"] == 1
    assert after["n_survey_models"] == 1


REPORTED_GROUPED = """
- source:
    paper_title: "A paper"
    doi: "10.1000/example"
  protocol_note: "Shared note."
  values:
    - {model: afmodel, task: ptbxl-multilabel, metric: auroc, value: 0.930, n: null}
    - {model: clocs, task: ptbxl-multilabel, metric: f1, value: 0.660, n: null,
       protocol_note: "Overridden for this value."}
"""


def test_reported_grouped_by_source(sandbox: Path) -> None:
    """One block per paper: the citation is written once, not copy-pasted onto each value.

    That duplication is what let a protocol note drift out of step with the source beside it,
    and what made adding a paper's whole comparison table tedious enough to skip.
    """
    _write_reported(sandbox, REPORTED_GROUPED)
    rc, out = run_validate(sandbox)
    assert rc == 0, out
    _site, cells, _results = _build(sandbox)

    kit = next(c for c in cells if c["model"] == "afmodel" and c["task"] == "ptbxl-multilabel")
    assert kit["reported_doi"] == "10.1000/example", "source inherited from the block"
    assert kit["protocol_note"] == "Shared note."

    survey = next(c for c in cells if c["model"] == "clocs")
    assert survey["reported_doi"] == "10.1000/example"
    assert survey["protocol_note"] == "Overridden for this value."


def test_reported_flat_rows_still_parse(sandbox: Path) -> None:
    """The old shape keeps working, so no existing row has to be rewritten to add a new one."""
    _write_reported(sandbox, REPORTED_OK)
    assert run_validate(sandbox)[0] == 0
    _site, cells, _results = _build(sandbox)
    cell = next(c for c in cells if c["model"] == "afmodel" and c["task"] == "ptbxl-multilabel")
    assert cell["status"] == "reported" and cell["value"] == 0.812


def test_valueless_rows_are_split_out_not_dropped(sandbox: Path) -> None:
    """The results table shows rows with something to show; the rest are still emitted.

    Listing every never-trained architecture in the metric grid made it mostly em dashes --
    on LTAFDB, a row of nothing for every architecture. They move to a compact disclosure rather than
    disappearing, so the rule that no cell may be left blank still holds.
    """
    _site, _cells, results = _build(sandbox)

    for tid, r in results.items():
        shown, hidden = r["rows"], r["rows_no_data"]
        assert len(shown) + len(hidden) == r["n_models"], f"{tid}: rows went missing"
        assert r["n_no_data"] == len(hidden)
        # Nothing with a value may be hidden ...
        for row in hidden:
            assert not row["has_data"] and not row["is_reported"], f"{tid}: {row['model']}"
            assert all(m["value"] is None for m in row["metrics"].values())
        # ... and nothing shown may be valueless.
        for row in shown:
            assert row["has_data"] or row["is_reported"], f"{tid}: {row['model']}"

    # LTAFDB has no runs and no citations, so its main table is empty and the page says so
    # rather than rendering a header with nothing under it.
    assert results["ltafdb-binary"]["rows"] == []
    assert results["ltafdb-binary"]["n_no_data"] == results["ltafdb-binary"]["n_models"] > 0


def test_reported_unknown_model_still_refused(sandbox: Path) -> None:
    """Neither registered nor a survey slug is still an error."""
    _write_reported(sandbox, REPORTED_OK.replace("model: afmodel", "model: not-a-model"))
    rc, out = run_validate(sandbox)
    assert rc == 1 and "E_REPORTED_MODEL" in out


def _build(sandbox: Path):
    """Load common/build_site_data from the sandbox copy, not the live repo."""
    sys.path.insert(0, str(sandbox / "tools"))
    try:
        for mod in ("common", "build_site_data"):
            sys.modules.pop(mod, None)
        import build_site_data
        import common
        site = common.load_site(sandbox)
        cells, _ = common.build_cells(site)
        return site, cells, build_site_data.build_results(site, cells)
    finally:
        sys.path.remove(str(sandbox / "tools"))
        for mod in ("common", "build_site_data"):
            sys.modules.pop(mod, None)


REPORTED_AUROC = """
- model: afmodel
  task: ptbxl-multilabel
  metric: auroc
  value: 0.930
  n: null
  source:
    paper_title: "A paper"
    doi: "10.1000/example"
  protocol_note: "Authors' own split."
"""


def test_defects_follow_the_snapshot_kit_not_the_registry(sandbox: Path) -> None:
    """Re-exporting the registry must not retire a defect from numbers an older kit produced.

    A defect is capped by kit version. The registry is refreshed whenever an architecture is
    added upstream, so its version runs ahead of the snapshot's; reading the cap against it
    would drop the warning from results that still carry the defect.
    """
    import json

    site, _cells, _results = _build(sandbox)
    produced_by = site.manifest["produced_by"]["kit_version"]
    (sandbox / "_data" / "known_defects.yml").write_text(
        f'- id: probe-defect\n  datasets: [ltafdb]\n  kit_version_max: "{produced_by}"\n'
        '  severity: high\n  summary: "x"\n  detail: "x"\n', encoding="utf-8")
    reg_path = sandbox / "_data" / "registry.json"
    reg = json.loads(reg_path.read_text(encoding="utf-8"))
    reg["meta"]["kit_version"] = "99.0.0"
    reg_path.write_text(json.dumps(reg), encoding="utf-8")

    _site, cells, _results = _build(sandbox)
    ltafdb = [c for c in cells if c["task"] == "ltafdb-binary"]
    assert ltafdb and all(c["defects"] == ["probe-defect"] for c in ltafdb)


def test_reported_non_primary_metric_gets_a_column_and_a_value(sandbox: Path) -> None:
    """The load-bearing case: the ECG literature reports AUROC where this site ranks on F1.

    Before the column derivation was widened, a published AUROC validated and then rendered
    as a status chip with an em dash, because build_results read every value from the
    snapshot aggregate alone.
    """
    _write_reported(sandbox, REPORTED_AUROC)
    assert run_validate(sandbox)[0] == 0
    _site, _cells, results = _build(sandbox)
    r = results["ptbxl-multilabel"]
    row = next(x for x in r["rows"] if x["model"] == "afmodel")

    assert "auroc" in r["columns"]
    assert row["metrics"]["auroc"]["value"] == 0.930
    assert row["metrics"]["auroc"]["display"] == "0.930"
    assert row["metrics"]["auroc"]["status"] == "reported"
    assert row["reported_doi"] == "10.1000/example"
    # Status is per metric: the unmeasured primary metric must not borrow the amber.
    assert row["metrics"]["f1"]["value"] is None
    assert row["metrics"]["f1"]["status"] == "not_run"


def test_reported_row_is_never_ranked_or_charted(sandbox: Path) -> None:
    """A published number beside a measured one, ranked, is the comparison the bucket forbids."""
    _write_reported(sandbox, REPORTED_AUROC)
    site, _cells, results = _build(sandbox)
    r = results["ptbxl-multilabel"]
    row = next(x for x in r["rows"] if x["model"] == "afmodel")

    assert row["is_reported"] is True
    assert row["has_data"] is False, "has_data gates ranking; a paper's number must not raise it"
    assert row["status"] == "reported"

    sys.path.insert(0, str(sandbox / "tools"))
    try:
        for mod in ("common", "build_site_data"):
            sys.modules.pop(mod, None)
        import build_site_data
        svg = build_site_data.svg_task_bars(site, r)
    finally:
        sys.path.remove(str(sandbox / "tools"))
        for mod in ("common", "build_site_data"):
            sys.modules.pop(mod, None)
    assert "AFModel" not in svg, "a reported value must not draw a bar in a ranked chart"

    # Reported rows sit after the ranked block, and are ordered by name rather than by value
    # -- sorting them would imply a shared scale with the measured rows above.
    order = [x["model"] for x in r["rows"]]
    measured = [i for i, x in enumerate(r["rows"]) if x["has_data"]]
    assert max(measured) < order.index("afmodel")
    # Valueless rows are no longer in the metric grid at all; they have their own list.
    assert all(x["has_data"] or x["is_reported"] for x in r["rows"])
    assert "afmodel" not in [x["model"] for x in r["rows_no_data"]]


def test_reported_on_a_task_with_no_snapshot_rows(sandbox: Path) -> None:
    """LTAFDB carries no measured rows at all, so its columns come only from reported.yml."""
    _write_reported(sandbox, REPORTED_AUROC.replace("ptbxl-multilabel", "ltafdb-binary"))
    assert run_validate(sandbox)[0] == 0
    _site, _cells, results = _build(sandbox)
    r = results["ltafdb-binary"]
    assert "auroc" in r["columns"], "a dataset with no snapshot rows still needs the column"
    row = next(x for x in r["rows"] if x["model"] == "afmodel")
    assert row["metrics"]["auroc"]["display"] == "0.930"


def test_reported_other_metric_surfaces_on_the_cell(sandbox: Path) -> None:
    """The cell keeps its honest status, but must not hide that a published value exists."""
    _write_reported(sandbox, REPORTED_AUROC)
    _site, cells, _results = _build(sandbox)
    cell = next(c for c in cells
                if c["model"] == "afmodel" and c["task"] == "ptbxl-multilabel")
    # An AUROC cannot fill a macro-F1 cell, so the status stays truthful ...
    assert cell["status"] == "not_run"
    assert cell["value"] is None
    # ... but the citation and the value are still reachable from the coverage page.
    assert cell["reported_other"] == "auroc 0.930"
    assert cell["reported_doi"] == "10.1000/example"


def test_status_without_a_bucket(sandbox: Path) -> None:
    p = sandbox / "_data" / "statuses.yml"
    p.write_text(p.read_text(encoding="utf-8").replace("  bucket: kit\n", "\n", 1),
                 encoding="utf-8")
    rc, out = run_validate(sandbox)
    assert rc == 1 and "E_STATUS_BUCKET" in out


def test_status_colour_disagreeing_with_its_bucket(sandbox: Path) -> None:
    """The legend shows one swatch per bucket, so a status may not render its own colour."""
    p = sandbox / "_data" / "statuses.yml"
    p.write_text(p.read_text(encoding="utf-8").replace(
        '  color_light: "#1B7F4B"', '  color_light: "#123456"', 1), encoding="utf-8")
    rc, out = run_validate(sandbox)
    assert rc == 1 and "E_STATUS_BUCKET_COLOUR" in out


def test_orphan_bucket(sandbox: Path) -> None:
    p = sandbox / "_data" / "buckets.yml"
    p.write_text(p.read_text(encoding="utf-8")
                 + '\nghost:\n  label: "Ghost"\n  order: 9\n  glyph: "?"\n'
                   '  color_light: "#000000"\n  color_dark: "#ffffff"\n  blurb: "x"\n',
                 encoding="utf-8")
    rc, out = run_validate(sandbox)
    assert rc == 1 and "E_BUCKET_ORPHAN" in out
