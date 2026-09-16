"""Verify every internal link and asset reference in the built site resolves.

Only internal targets: external links go stale for reasons outside this repo and would make
the build fail for someone else's outage. A broken internal link, by contrast, is always our
bug and is always fixable.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urldefrag

ATTR = re.compile(r'(?:href|src)="([^"]+)"')
EXTERNAL = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|//|#|mailto:|data:)", re.I)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("site", type=Path)
    ap.add_argument("--baseurl", default="/deepecg-kit-bench")
    ap.add_argument("--internal-only", action="store_true", default=True)
    ap.add_argument("--fail-on-404", action="store_true", default=True)
    args = ap.parse_args(argv)

    site: Path = args.site
    if not site.is_dir():
        print(f"error: {site} does not exist; run the build first.", file=sys.stderr)
        return 2

    broken: list[tuple[str, str]] = []
    checked = 0
    for page in sorted(site.rglob("*.html")):
        for raw in ATTR.findall(page.read_text(encoding="utf-8", errors="replace")):
            target, _ = urldefrag(raw)
            if not target or EXTERNAL.match(target):
                continue
            checked += 1
            path = unquote(target)
            if path.startswith(args.baseurl):
                path = path[len(args.baseurl):]
            rel = path.lstrip("/")
            candidate = site / rel
            ok = (
                candidate.is_file()
                or (candidate / "index.html").is_file()
                or (candidate.is_dir() and rel.endswith("/"))
            )
            if not ok:
                broken.append((str(page.relative_to(site)), raw))

    if broken:
        print(f"{len(broken)} broken internal reference(s) of {checked} checked:\n", file=sys.stderr)
        for src, target in sorted(set(broken)):
            print(f"  {src} -> {target}", file=sys.stderr)
        return 1 if args.fail_on_404 else 0

    print(f"check_links: OK ({checked} internal references across "
          f"{len(list(site.rglob('*.html')))} pages)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
