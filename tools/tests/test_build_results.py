"""tools/build_results.py turns the library's two CSVs into results.json without touching a number."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import build_results

METRICS_HEADER = "dataset,model,metric,averaging,n_runs,n,mean,std,sem,lower_ci,upper_ci,seeds"
RUNS_HEADER = "run_dir,model,dataset,seed,averaging,multi_label,n_train,n_val,n_test,n_test_groups,metric,value"


@pytest.fixture
def site(tmp_path: Path) -> Path:
    """A two-task, two-architecture site with nothing published yet."""
    data = tmp_path / "site" / "data"
    data.mkdir(parents=True)
    (data / "catalogue.json").write_text(json.dumps({
        "tasks": [{"id": "task-a", "dataset": "ds-a"}, {"id": "task-b", "dataset": "ds-b"}],
        "metrics": [{"id": "f1"}, {"id": "auroc"}],
    }))
    (data / "registry.json").write_text(json.dumps({"models": {"net": {}, "other": {}}}))
    return tmp_path / "site"


def write_aggregate(folder: Path, metric_rows: list[str], run_rows: list[str]) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "seed_metrics_long.csv").write_text("\n".join([METRICS_HEADER, *metric_rows]) + "\n")
    (folder / "seed_runs_long.csv").write_text("\n".join([RUNS_HEADER, *run_rows]) + "\n")
    return folder


def seeded(tmp_path: Path) -> Path:
    """net on ds-a over seeds 42 and 43; AUROC is undefined (NaN) for seed 43."""
    return write_aggregate(
        tmp_path / "agg",
        [
            "ds-a,net,auroc,macro,2,1,0.9,,,,,42",
            "ds-a,net,f1,macro,2,2,0.75,0.07071067811865474,0.05,0.11,1.39,42;43",
        ],
        [
            # Deliberately out of seed order, and with the trainer's absolute paths.
            "/gpu/runs/net-ds-a-seed43,net,ds-a,43,macro,False,,,,,f1,0.8",
            "/gpu/runs/net-ds-a-seed42,net,ds-a,42,macro,False,,,,,f1,0.7",
            "/gpu/runs/net-ds-a-seed43,net,ds-a,43,macro,False,,,,,auroc,nan",
            "/gpu/runs/net-ds-a-seed42,net,ds-a,42,macro,False,,,,,auroc,0.9",
        ],
    )


def run(site: Path, agg: Path, *extra: str) -> tuple[int, dict | None]:
    code = build_results.main([str(agg), "--site", str(site), "--generated", "2026-01-01T00:00:00Z", *extra])
    out = site / "data" / "results.json"
    return code, json.loads(out.read_text()) if out.exists() else None


def test_numbers_pass_through_untouched(site: Path, tmp_path: Path) -> None:
    code, results = run(site, seeded(tmp_path), "--kit-version", "9.9.9")
    assert code == 0
    assert results["kit_version"] == "9.9.9" and results["n_runs"] == 2 and results["schema"] == 1
    (row,) = results["rows"]
    assert (row["model"], row["task"], row["averaging"], row["runs"], row["seeds"]) == (
        "net", "task-a", "macro", 2, [42, 43])
    assert row["metrics"]["f1"] == {
        "n": 2, "mean": 0.75, "std": 0.07071067811865474, "lo": 0.11, "hi": 1.39, "values": [0.7, 0.8]}
    assert list(row["metrics"]) == ["f1", "auroc"], "metrics follow the catalogue's order"


def test_nan_becomes_null_so_the_browser_can_parse_it(site: Path, tmp_path: Path) -> None:
    _, results = run(site, seeded(tmp_path))
    auroc = results["rows"][0]["metrics"]["auroc"]
    assert auroc == {"n": 1, "mean": 0.9, "std": None, "lo": None, "hi": None, "values": [0.9, None]}
    assert "NaN" not in (site / "data" / "results.json").read_text()


def test_a_metric_no_run_could_compute_is_left_out(site: Path, tmp_path: Path) -> None:
    """Per-label scaling has no value on a softmax task; an empty entry would claim it was measured."""
    agg = write_aggregate(
        tmp_path / "agg",
        [
            "ds-a,net,f1,macro,1,1,0.7,,,,,42",
            "ds-a,net,auroc,macro,1,0,,,,,,",
        ],
        [
            "/gpu/runs/net-ds-a-seed42,net,ds-a,42,macro,False,,,,,f1,0.7",
            "/gpu/runs/net-ds-a-seed42,net,ds-a,42,macro,False,,,,,auroc,",
        ],
    )
    code, results = run(site, agg)
    assert code == 0
    assert list(results["rows"][0]["metrics"]) == ["f1"]


def test_seedless_runs_have_no_seed_and_no_averaging(site: Path, tmp_path: Path) -> None:
    agg = write_aggregate(
        tmp_path / "agg",
        ["ds-b,other,f1,unknown,1,1,0.5,,,,,-1"],
        ["/old/20260101-000000-other-ds-b,other,ds-b,-1,unknown,False,,,,,f1,0.5"],
    )
    _, results = run(site, agg)
    (row,) = results["rows"]
    assert row["seeds"] == [] and row["averaging"] is None and row["plot_seed"] is None


@pytest.mark.parametrize(
    ("line", "message"),
    [
        ("ds-x,net,f1,macro,1,1,0.5,,,,,42", "unknown dataset 'ds-x'"),
        ("ds-a,ghost,f1,macro,1,1,0.5,,,,,42", "unknown model 'ghost'"),
        ("ds-a,net,kappa,macro,1,1,0.5,,,,,42", "unknown metric 'kappa'"),
    ],
)
def test_anything_unknown_is_refused(site: Path, tmp_path: Path, capsys, line: str, message: str) -> None:
    code, results = run(site, write_aggregate(tmp_path / "agg", [line], []))
    assert code == 1 and results is None, "nothing may be written when the input cannot be joined"
    assert message in capsys.readouterr().err


def test_a_dataset_shared_by_two_tasks_is_refused(site: Path, tmp_path: Path) -> None:
    catalogue = site / "data" / "catalogue.json"
    data = json.loads(catalogue.read_text())
    data["tasks"][1]["dataset"] = "ds-a"
    catalogue.write_text(json.dumps(data))
    with pytest.raises(SystemExit, match="belongs to two tasks"):
        run(site, seeded(tmp_path))


def test_plots_come_from_the_lowest_seed_found_by_directory_name(site: Path, tmp_path: Path) -> None:
    runs = tmp_path / "runs"
    for seed, marker in ((42, b"from-42"), (43, b"from-43")):
        folder = runs / f"net-ds-a-seed{seed}"
        folder.mkdir(parents=True)
        (folder / "confusion_matrix.png").write_bytes(marker)
        (folder / "loss.png").write_bytes(marker)
        (folder / "accuracy.png").write_bytes(marker)  # never collected
    stale = site / "plots" / "task-a" / "net"
    stale.mkdir(parents=True)
    (stale / "calibration-curve.png").write_bytes(b"left over from an earlier refresh")

    _, results = run(site, seeded(tmp_path), "--runs-dir", str(runs))
    (row,) = results["rows"]
    assert row["plots"] == ["confusion-matrix", "loss-curve"] and row["plot_seed"] == 42
    assert sorted(p.name for p in stale.iterdir()) == ["confusion-matrix.png", "loss-curve.png"]
    assert (stale / "confusion-matrix.png").read_bytes() == b"from-42"


def test_without_runs_the_published_plots_are_listed_as_they_are(site: Path, tmp_path: Path) -> None:
    folder = site / "plots" / "task-a" / "net"
    folder.mkdir(parents=True)
    (folder / "loss-curve.png").write_bytes(b"x")
    (folder / "confusion-matrix.png").write_bytes(b"x")
    _, results = run(site, seeded(tmp_path))
    assert results["rows"][0]["plots"] == ["confusion-matrix", "loss-curve"]
    assert results["rows"][0]["plot_seed"] is None


def test_an_incomplete_directory_is_refused(site: Path, tmp_path: Path, capsys) -> None:
    (tmp_path / "empty").mkdir()
    code, results = run(site, tmp_path / "empty")
    assert code == 1 and results is None
    assert "seed_metrics_long.csv" in capsys.readouterr().err
