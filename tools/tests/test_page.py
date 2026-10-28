"""The page, loaded in a real browser from the same sub-path GitHub Pages serves it under.

Everything else in this suite checks the parts; this checks that they add up to a drawn
table. It needs Chrome or Chromium and is skipped where there is none (set CHROME to
point at a binary).
"""

from __future__ import annotations

import functools
import json
import os
import re
import shutil
import subprocess
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SITE = REPO / "site"
SUBPATH = "deepecg-kit-bench"

CANDIDATES = (
    os.environ.get("CHROME"),
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
)


def find_chrome() -> str | None:
    for candidate in filter(None, CANDIDATES):
        found = shutil.which(candidate) or (candidate if Path(candidate).is_file() else None)
        if found:
            return found
    return None


CHROME = find_chrome()
pytestmark = pytest.mark.skipif(CHROME is None, reason="no Chrome or Chromium found; set CHROME")


class Handler(SimpleHTTPRequestHandler):
    statuses: list[tuple[int, str]] = []

    def log_request(self, code="-", size="-") -> None:  # noqa: ARG002 - the base signature
        self.statuses.append((int(code), self.path))

    def log_message(self, *args) -> None:  # keep the test output clean
        pass


@pytest.fixture(scope="module")
def served(tmp_path_factory: pytest.TempPathFactory):
    """site/ mounted at /deepecg-kit-bench/, so a root-absolute URL would show up as a 404."""
    root = tmp_path_factory.mktemp("pages")
    (root / SUBPATH).symlink_to(SITE, target_is_directory=True)
    Handler.statuses = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(root)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}/{SUBPATH}/"
    server.shutdown()
    thread.join()


def render(url: str, tmp_path: Path) -> str:
    """The DOM after the page's scripts and fetches have run."""
    result = subprocess.run(
        [CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--no-first-run",
         f"--user-data-dir={tmp_path / 'profile'}", "--virtual-time-budget=15000",
         "--dump-dom", url],
        capture_output=True, text=True, timeout=120, check=False,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    return result.stdout


def data(name: str) -> dict:
    return json.loads((SITE / "data" / f"{name}.json").read_text(encoding="utf-8"))


def test_the_table_is_drawn_from_the_data(served: str, tmp_path: Path) -> None:
    dom = render(served, tmp_path)
    assert 'data-ready="true"' in dom, "app.js did not finish; the fallback text is still showing"

    # Listed: architectures whose catalogue entry cites a paper or code, and the tasks not hidden.
    registered, prose = data("registry")["models"], data("catalogue")["models"]
    listed = [m for m in prose if m["name"] in registered and (m.get("paper") or m.get("code_url"))]
    names = {m["name"] for m in listed}
    tasks = [t for t in data("catalogue")["tasks"] if not t.get("hidden")]
    pairs = [r for r in data("results")["rows"] if r["model"] in names and r["task"] in {t["id"] for t in tasks}]
    assert len(re.findall(r'<tr class="row"', dom)) == len(listed)
    assert len(re.findall(r'<th scope="col"', dom)) == 3 + len(tasks)
    papers = [m for m in listed if m.get("paper")]
    assert len(re.findall(r'<td class="ref"><a href="https://', dom)) == len(papers)
    with_f1 = sum(1 for row in pairs if row["metrics"].get("f1", {}).get("mean") is not None)
    assert len(re.findall(r'<span class="val(?: best)?">', dom)) == with_f1
    pressed = re.findall(r'<button class="filter-btn active"[^>]*aria-pressed="true"[^>]*>([^<]*)</button>', dom)
    assert pressed == ["All", "F1"], "the family and metric pills start on All and F1"

    failed = [(code, path) for code, path in Handler.statuses if code >= 400]
    assert not failed, f"the page asked for something that is not published: {failed}"


def test_a_link_to_one_architecture_opens_it(served: str, tmp_path: Path) -> None:
    name = data("results")["rows"][0]["model"]
    dom = render(f"{served}?model={name}", tmp_path)
    panels = re.findall(r'<tr class="panel-row" id="panel-([^"]+)"', dom)
    assert panels == [name], "exactly the linked architecture is open"
    toggle = re.search(rf'<button[^>]*aria-controls="panel-{re.escape(name)}"[^>]*>', dom)
    assert toggle and 'aria-expanded="true"' in toggle.group(0)
    assert "<img " in dom.split(f'id="panel-{name}"', 1)[1], "the panel shows its plots"
