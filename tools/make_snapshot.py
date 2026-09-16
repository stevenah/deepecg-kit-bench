"""Produce an immutable, manifested results snapshot from a set of run directories.

Wraps `deepecg aggregate` and `deepecg rank` so the two invocations cannot diverge, and
records enough provenance that a reader can tell what the numbers are and are not.

Three behaviours here are load-bearing, not conveniences:

1. `--on-duplicate error` is tried FIRST, always. deepecgkit resolves duplicate
   (dataset, model, seed) keys by filesystem mtime, and mtime does not survive cp, clone
   or rsync. Two operators running the identical documented command could otherwise
   publish different winners. Duplicates must be seen and accepted explicitly.
2. Both commands' stdout is teed to diagnostics.txt. The discovery counts
   (unreadable / no_seed / duplicate) and the averaging-conflict table are PRINTED by the
   CLI and written nowhere, so this file is currently the only record that they existed.
3. `--include-legacy` is refused unless the snapshot is declared preliminary or archival.
   Seedless runs pooled under a sentinel seed are archaeology; they must not quietly
   appear beside real replicates in a snapshot presented as current.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LEGACY_OK_STATUSES = {"preliminary", "archival"}
ALL_STATUSES = ["preliminary", "current", "archival", "superseded"]

AGGREGATE_OUTPUTS = ["seed_runs_long.csv", "seed_metrics_long.csv"]
RANK_OUTPUTS = ["seed_ranks.csv", "rank_distribution.csv", "kendall_tau.csv", "flip_tests.csv"]


def run_cli(deepecg: str, args: list[str]) -> tuple[int, str]:
    """Run a deepecg subcommand, returning (returncode, combined output)."""
    proc = subprocess.run([deepecg, *args], capture_output=True, text=True)
    return proc.returncode, proc.stdout + proc.stderr


def parse_diagnostics(text: str) -> dict[str, Any]:
    """Recover the discovery counters the CLI prints and never writes.

    The CLI emits "  <N> run(s) <reason>" per discovery bucket and
    "<N> runs across <M> dataset(s)" as its summary. Deliberately tolerant: a line we
    cannot parse leaves its counter null rather than guessing, and the raw transcript is
    committed beside this parse so a human can always check it.
    """
    out: dict[str, Any] = {
        "runs_usable": None,
        "n_datasets": None,
        "unreadable": None,
        "no_seed": None,
        "duplicate": None,
        "averaging_conflicts": None,
    }
    bucket = re.compile(r"^\s*(\d+)\s+runs?\(s\)?\s+(\w+)\s*$")
    bucket2 = re.compile(r"^\s*(\d+)\s+run\(s\)\s+(\w+)\s*$")
    summary = re.compile(r"^\s*(\d+)\s+runs?\s+across\s+(\d+)\s+dataset")
    for raw in text.splitlines():
        m = summary.match(raw)
        if m:
            out["runs_usable"] = int(m.group(1))
            out["n_datasets"] = int(m.group(2))
            continue
        m = bucket2.match(raw) or bucket.match(raw)
        if m and m.group(2) in out:
            out[m.group(2)] = int(m.group(1))
    # A bucket the CLI never printed is genuinely zero, not unknown: it prints a line per
    # non-empty bucket only. Only leave null what we could not determine at all.
    if out["runs_usable"] is not None:
        for k in ("unreadable", "no_seed", "duplicate"):
            if out[k] is None:
                out[k] = 0
    return out


def find_incomplete_runs(runs_dirs: list[Path], registry_path: Path) -> list[dict[str, Any]]:
    """Run directories that exist but produced no metrics file.

    discover_runs() globs */classification_metrics.csv, so a directory without one is not
    "unreadable" -- it is invisible. Recording it here is what lets the site render an
    `incomplete` cell instead of silently reporting the pair as never attempted, which is
    a different and less honest claim.

    Directory names are {timestamp}-{model}-{dataset}[-seed{N}] and both model and dataset
    names contain hyphens, so the split is resolved against the registered names rather
    than guessed positionally.
    """
    try:
        reg = json.loads(registry_path.read_text(encoding="utf-8"))
        models = sorted(reg.get("models", {}), key=len, reverse=True)
        datasets = sorted(reg.get("datasets", {}), key=len, reverse=True)
    except (OSError, ValueError):
        return []

    found: list[dict[str, Any]] = []
    for root in runs_dirs:
        if not root.is_dir():
            continue
        for child in sorted(root.iterdir()):
            if not child.is_dir() or child.name.startswith("_"):
                continue
            if (child / "classification_metrics.csv").is_file():
                continue
            name = child.name
            # Run dirs are {YYYYMMDD}-{HHMMSS}-{model}-{dataset}[-seed{N}]: the
            # timestamp is TWO hyphen-separated fields, not one.
            stem = re.sub(r"^\d{8}-\d{6}-", "", name)
            hit = None
            for m in models:
                if stem.startswith(m + "-"):
                    rest = stem[len(m) + 1 :]
                    for d in datasets:
                        if rest == d or rest.startswith(d + "-"):
                            hit = {"model": m, "dataset": d, "run_dir": child.name}
                            break
                if hit:
                    break
            found.append(hit or {"model": None, "dataset": None, "run_dir": child.name})
    return found


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def git_facts(repo: Path | None) -> dict[str, Any]:
    if repo is None or not (repo / ".git").exists():
        return {"kit_git_sha": None, "kit_git_dirty": None}

    def run(*a: str) -> str | None:
        try:
            return subprocess.run(
                ["git", "-C", str(repo), *a], capture_output=True, text=True, check=True
            ).stdout.strip()
        except (subprocess.CalledProcessError, OSError):
            return None

    sha = run("rev-parse", "HEAD")
    dirty = run("status", "--porcelain")
    return {
        "kit_git_sha": sha[:12] if sha else None,
        "kit_git_dirty": bool(dirty) if dirty is not None else None,
    }


def kit_versions(deepecg: str) -> dict[str, Any]:
    """Ask the interpreter that owns the CLI for its own versions."""
    python = str(Path(deepecg).with_name("python"))
    code = (
        "import json,sys;"
        "d={'python':sys.version.split()[0]};"
        "\nimport deepecgkit; d['kit_version']=getattr(deepecgkit,'__version__',None)\n"
        "try:\n import torch; d['torch']=torch.__version__\nexcept Exception: d['torch']=None\n"
        "print(json.dumps(d))"
    )
    try:
        out = subprocess.run([python, "-c", code], capture_output=True, text=True, check=True)
        return json.loads(out.stdout.strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        return {"python": None, "kit_version": None, "torch": None}


def yaml_dump(obj: Any, indent: int = 0) -> str:
    """Minimal YAML writer, so this tool needs no import beyond the stdlib."""
    pad = "  " * indent
    lines: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (dict, list)) and v:
                lines.append(f"{pad}{k}:")
                lines.append(yaml_dump(v, indent + 1))
            elif isinstance(v, (dict, list)):
                lines.append(f"{pad}{k}: {{}}" if isinstance(v, dict) else f"{pad}{k}: []")
            else:
                lines.append(f"{pad}{k}: {scalar(v)}")
    elif isinstance(obj, list):
        for v in obj:
            if isinstance(v, dict):
                inner = yaml_dump(v, indent + 1).lstrip()
                lines.append(f"{pad}- {inner}")
            else:
                lines.append(f"{pad}- {scalar(v)}")
    return "\n".join(lines)


def scalar(v: Any) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    if s == "" or any(c in s for c in ':#{}[]&*!|>%@`"\n') or s.strip() != s:
        return json.dumps(s, ensure_ascii=False)
    return s


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--id", required=True, help="Snapshot id; becomes a permanent URL segment")
    p.add_argument("--label", required=True, help="One-line human description")
    p.add_argument("--status", required=True, choices=ALL_STATUSES)
    p.add_argument("--runs-dir", nargs="+", required=True, type=Path)
    p.add_argument("--kit-repo", type=Path, default=None)
    p.add_argument("--deepecg", default="deepecg", help="Path to the deepecg entry point")
    p.add_argument("--metric", default="f1", help="Metric to rank on")
    p.add_argument("--confidence-level", type=float, default=0.95)
    p.add_argument("--recursive", action="store_true")
    p.add_argument("--include-legacy", action="store_true")
    p.add_argument("--accept-duplicates", action="store_true",
                   help="Re-run with --on-duplicate newest after an explicit duplicate report")
    p.add_argument("--supersedes", default=None)
    p.add_argument("--out-root", type=Path, default=Path("results/snapshots"))
    p.add_argument("--force", action="store_true", help="Overwrite an existing snapshot (do not)")
    args = p.parse_args(argv)

    if args.include_legacy and args.status not in LEGACY_OK_STATUSES:
        p.error(
            f"--include-legacy requires --status in {sorted(LEGACY_OK_STATUSES)}; got "
            f"'{args.status}'. Seedless runs pooled under a sentinel seed must never appear "
            f"in a snapshot presented as current."
        )

    target = args.out_root / args.id
    if target.exists() and not args.force:
        print(f"error: {target} already exists. Snapshots are immutable; pick a new --id.", file=sys.stderr)
        return 2
    target.mkdir(parents=True, exist_ok=True)

    # ---- one flag list, shared by both commands, so they cannot see different data ----
    shared: list[str] = []
    for d in args.runs_dir:
        shared.extend([])
    shared = ["--runs-dir", *[str(d) for d in args.runs_dir],
              "--output-dir", str(target),
              "--confidence-level", str(args.confidence_level)]
    if args.recursive:
        shared.append("--recursive")
    if args.include_legacy:
        shared.append("--include-legacy")

    transcript: list[str] = []
    on_duplicate = "error"

    def attempt(dup_mode: str) -> tuple[int, str, list[str]]:
        agg = [*shared, "--on-duplicate", dup_mode, "--emit-latex"]
        rc, out = run_cli(args.deepecg, ["aggregate", *agg])
        return rc, out, agg

    rc, out, agg_args = attempt("error")
    transcript.append("$ deepecg aggregate " + " ".join(agg_args))
    transcript.append(out)

    if rc != 0:
        if not args.accept_duplicates:
            print(out)
            print(
                "\nerror: aggregate failed under --on-duplicate error.\n"
                "If the cause is duplicate run directories, inspect them and re-run with\n"
                "--accept-duplicates once you have decided that resolving by mtime is\n"
                "acceptable. Do not pass it reflexively: mtime does not survive cp/rsync,\n"
                "so the winner is not reproducible across machines.",
                file=sys.stderr,
            )
            shutil.rmtree(target, ignore_errors=True)
            return 1
        on_duplicate = "newest"
        rc, out, agg_args = attempt("newest")
        transcript.append("$ deepecg aggregate " + " ".join(agg_args))
        transcript.append(out)
        if rc != 0:
            print(out, file=sys.stderr)
            shutil.rmtree(target, ignore_errors=True)
            return 1

    rank_args = [*shared, "--on-duplicate", on_duplicate, "--metric", args.metric, "--emit-latex"]
    rrc, rout = run_cli(args.deepecg, ["rank", *rank_args])
    transcript.append("$ deepecg rank " + " ".join(rank_args))
    transcript.append(rout)
    if rrc != 0:
        print(rout, file=sys.stderr)
        print("warning: rank failed; snapshot will carry aggregate output only.", file=sys.stderr)

    diagnostics_text = "\n".join(transcript)
    (target / "diagnostics.txt").write_text(diagnostics_text, encoding="utf-8")

    produced = sorted(f.name for f in target.iterdir() if f.suffix in {".csv", ".tex"})
    missing = [f for f in AGGREGATE_OUTPUTS if not (target / f).is_file()]
    if missing:
        print(f"error: aggregate produced no {missing}; nothing to publish.", file=sys.stderr)
        shutil.rmtree(target, ignore_errors=True)
        return 1

    # ---- schema flags: what this snapshot's CSVs can and cannot support -------------
    header = (target / "seed_metrics_long.csv").read_text(encoding="utf-8").splitlines()[:1]
    metrics_present: set[str] = set()
    import csv as _csv

    with (target / "seed_metrics_long.csv").open(encoding="utf-8") as fh:
        for row in _csv.DictReader(fh):
            metrics_present.add(row.get("metric", ""))
    averagings = set()
    with (target / "seed_runs_long.csv").open(encoding="utf-8") as fh:
        seeds: set[str] = set()
        for row in _csv.DictReader(fh):
            averagings.add(row.get("averaging", ""))
            seeds.add(row.get("seed", ""))

    versions = kit_versions(args.deepecg)
    manifest = {
        "schema_version": 1,
        "id": args.id,
        "label": args.label,
        "status": args.status,
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "supersedes": args.supersedes,
        "produced_by": {
            "kit_version": versions.get("kit_version"),
            "python": versions.get("python"),
            "torch": versions.get("torch"),
            **git_facts(args.kit_repo),
        },
        "commands": [
            "deepecg aggregate " + " ".join(agg_args),
            "deepecg rank " + " ".join(rank_args),
        ],
        "runs_dirs": [str(d) for d in args.runs_dir],
        "protocol": {
            "replicate_kind": "unknown" if args.include_legacy else "seed",
            "replicate_ids": sorted(seeds),
            "rank_metric": args.metric,
            "confidence_level": args.confidence_level,
            "interval_kind": "student-t-over-replicates",
            "bootstrap_ci": "not-measured",
            "on_duplicate": on_duplicate,
            "include_legacy": args.include_legacy,
        },
        "discovery": parse_diagnostics(diagnostics_text),
        "incomplete_runs": find_incomplete_runs(list(args.runs_dir), Path("_data/registry.json")),
        "schema_flags": {
            "calibration_metrics_present": bool(metrics_present & {"ece", "brier", "mce"}),
            "average_column_present": bool(averagings & {"macro", "binary"}),
            "observed_averagings": sorted(a for a in averagings if a),
            "metrics_present": sorted(m for m in metrics_present if m),
        },
        "zenodo_doi": None,
        "files": produced + ["diagnostics.txt"],
    }
    (target / "manifest.yml").write_text(yaml_dump(manifest) + "\n", encoding="utf-8")

    checks = [f for f in sorted(target.iterdir()) if f.name != "CHECKSUMS.sha256"]
    (target / "CHECKSUMS.sha256").write_text(
        "".join(f"{sha256_file(f)}  {f.name}\n" for f in checks), encoding="utf-8"
    )

    print(f"\nsnapshot {args.id} written to {target}")
    print(f"  status            {args.status}")
    print(f"  on_duplicate      {on_duplicate}")
    print(f"  replicate ids     {sorted(seeds)}")
    print(f"  averagings seen   {sorted(a for a in averagings if a)}")
    print(f"  metrics present   {len(metrics_present)}")
    print(f"  files             {len(checks)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
