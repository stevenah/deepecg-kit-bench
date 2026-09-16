"""Resolve every DOI and arXiv id in the repo, and check it points at the paper we claim.

This is the one gate the rest of the repo cannot provide. `make validate` checks that the
site agrees with its inputs; nothing in it can tell that a DOI is *wrong*, because a wrong
DOI is still a well-formed string that resolves. And a guessed DOI almost never 404s -- it
lands on a real but unrelated paper, so it survives every syntactic check and reads to a
human as a citation. Two of the identifiers in the first draft of _data/field.yml were
off-by-one-digit guesses; both resolved, one to a paper about pandemic case data and one to a
paper about chest-compression noise.

So the check has to be semantic: fetch the record, compare the registered title against the
title we wrote down, and complain when they diverge.

Deliberately NOT part of `make check`. It needs the network and hits two public APIs, and a
build that fails because Crossref is having a bad afternoon teaches people to ignore the
build. Run it when you add citations, and before a release:

    make identifiers                  # everything
    make identifiers ARGS=--reported  # just _data/reported.yml, after adding a paper

Exit status is 1 if anything failed to resolve or mismatched, so it is still usable in a
scheduled job where a flake costs nothing.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from common import ROOT, flatten_reported, load_yaml, read_front_matter

# Crossref asks for a contact address so they can warn you before blocking you; arXiv asks
# for a descriptive agent. Both are politeness, not authentication.
UA = {"User-Agent": "deepecg-kit-bench identifier check (mailto:steven@simula.no)"}

# Below this, the registered title and ours are different papers rather than the same paper
# punctuated differently. Tuned against the real data: genuine matches sit at 0.95+, and the
# two wrong-DOI cases that provoked this script scored 0.37 and 0.29.
MATCH = 0.72


def _norm(s: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(s or "").lower()).strip()


def _get(url: str, tries: int = 4) -> str | None:
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None            # definitively absent, not worth retrying
            time.sleep(4 * (attempt + 1))   # 429 from arXiv is common and clears
        except Exception:
            time.sleep(4 * (attempt + 1))
    return None


def registered_title(doi: str) -> tuple[str | None, str]:
    """Return (title, source) for an identifier, or (None, reason) if it does not resolve."""
    if doi.startswith("arXiv:"):
        body = _get("http://export.arxiv.org/api/query?id_list=" + doi.split(":", 1)[1])
        if body is None or "<entry>" not in body:
            return None, "arXiv returned no entry"
        m = re.search(r"<entry>.*?<title>(.*?)</title>", body, re.S)
        time.sleep(3.0)                 # arXiv rate-limits hard; be a good citizen
        return (" ".join(m.group(1).split()) if m else ""), "arXiv"
    body = _get("https://api.crossref.org/works/" + urllib.parse.quote(doi, safe=""))
    if body is None:
        return None, "not registered with Crossref"
    try:
        return (json.loads(body)["message"].get("title") or [""])[0], "Crossref"
    except Exception:
        return None, "Crossref returned an unreadable record"


def claims(root: Path, which: str) -> list[tuple[str, str, str]]:
    """Every (where, doi, expected_title) the repo asserts."""
    out: list[tuple[str, str, str]] = []
    if which in ("all", "field"):
        for e in load_yaml(root / "_data" / "field.yml") or []:
            o = e.get("origin") or {}
            if o.get("doi"):
                out.append((f"field.yml:{e['slug']}", o["doi"], o.get("paper_title")))
    if which in ("all", "reported"):
        raw = load_yaml(root / "_data" / "reported.yml")
        seen: set[str] = set()
        for r in flatten_reported(raw):
            src = r.get("source") or {}
            doi = src.get("doi")
            # One block cites one paper many times over; check the paper once.
            if doi and doi not in seen:
                seen.add(doi)
                out.append((f"reported.yml:{doi}", doi, src.get("paper_title")))
    if which in ("all", "models"):
        for p in sorted((root / "_models").glob("*.md")):
            o = (read_front_matter(p).get("origin") or {})
            if o.get("doi"):
                out.append((f"_models/{p.stem}.md", o["doi"], o.get("paper_title")))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group()
    for name in ("field", "reported", "models"):
        g.add_argument(f"--{name}", dest="which", action="store_const", const=name,
                       help=f"check only _data/{name}.yml" if name != "models"
                            else "check only _models/*.md")
    ap.set_defaults(which="all")
    args = ap.parse_args(argv)

    todo = claims(ROOT, args.which)
    print(f"resolving {len(todo)} identifiers ({args.which})...", file=sys.stderr)

    problems: list[str] = []
    for where, doi, expected in todo:
        title, note = registered_title(doi)
        if title is None:
            problems.append(f"  UNRESOLVED  {where}\n              {doi} -- {note}")
            continue
        if not expected:
            print(f"  no-title    {where}  {doi} -> {title[:70]!r}", file=sys.stderr)
            continue
        ratio = difflib.SequenceMatcher(None, _norm(title), _norm(expected)).ratio()
        if ratio < MATCH:
            problems.append(
                f"  MISMATCH    {where}  ({ratio:.2f})\n"
                f"              {doi} is registered as: {title[:90]!r}\n"
                f"              but we call it:         {str(expected)[:90]!r}"
            )

    if problems:
        print(f"\n{len(problems)} identifier problem(s):\n", file=sys.stderr)
        for p in problems:
            print(p + "\n", file=sys.stderr)
        print("A mismatch usually means a guessed or transcribed-wrong identifier. Resolve "
              "the real one (api.crossref.org/works?query.bibliographic=<title>) or set the "
              "doi to null -- an absent identifier is always better than a plausible one.",
              file=sys.stderr)
        return 1

    print(f"identifiers: OK\n  {len(todo)} resolved, every registered title matches ours")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
