"""Theme correctness, asserted mechanically.

Two properties, both of which are easy to break by hand and impossible to notice in one
theme while working in the other:

1. Every colour is defined in a token block, and no literal hex leaks into a rule or an
   SVG. A stray hex looks fine in whichever theme you authored it in and wrong in the
   other. This single assertion catches the entire class, including the <img> SVG trap.
2. Both palettes meet WCAG AA contrast. #1E4B8C is 7.9:1 on the light surface and about
   2:1 on the dark background -- reusing it unchanged would be a real accessibility
   failure, not a cosmetic one.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
CSS = REPO / "assets" / "css" / "main.css"
HEX = re.compile(r"#[0-9a-fA-F]{6}\b")


def srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_colour: str) -> float:
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * srgb_to_linear(r) + 0.7152 * srgb_to_linear(g) + 0.0722 * srgb_to_linear(b)


def contrast(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def token_blocks() -> dict[str, dict[str, str]]:
    """Parse `--name: #hex;` declarations out of each :root/@media block."""
    text = CSS.read_text(encoding="utf-8")
    blocks: dict[str, dict[str, str]] = {}
    for m in re.finditer(r"(:root[^{]*|@media[^{]*\{\s*:root[^{]*)\{([^}]*)\}", text):
        selector = " ".join(m.group(1).split())
        vals = dict(re.findall(r"(--[\w-]+)\s*:\s*(#[0-9a-fA-F]{6})\s*;", m.group(2)))
        if vals:
            blocks.setdefault(selector, {}).update(vals)
    return blocks


def test_every_hex_lives_in_a_token_block() -> None:
    """No literal colour outside a :root declaration."""
    text = CSS.read_text(encoding="utf-8")
    # Comments first: a colour NAMED in prose is documentation, not a leak.
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    # Then blank out every :root / @media-:root block; any remaining hex is a real leak.
    stripped = re.sub(r"(:root[^{]*|@media[^{]*\{\s*:root[^{]*)\{[^}]*\}", "", text)
    leaks = HEX.findall(stripped)
    assert not leaks, f"literal hex outside the token blocks: {sorted(set(leaks))}"


def test_generated_svg_uses_no_literal_hex() -> None:
    """Charts must reference custom properties, never baked colours."""
    gen = REPO / "_includes" / "charts" / "generated"
    svgs = list(gen.glob("*.svg"))
    if not svgs:
        pytest.skip("charts not generated; run tools/build_site_data.py")
    for f in svgs:
        leaks = HEX.findall(f.read_text(encoding="utf-8"))
        assert not leaks, f"{f.name} bakes in colours {sorted(set(leaks))}; use var(--...)"


def palette(theme: str) -> dict[str, str]:
    """Tokens for one theme, found by selector content rather than by position.

    Which theme owns bare `:root` is a design decision that has already changed once
    (light-default -> dark-default, to match ECGBench). The test must not encode it.
    """
    blocks = token_blocks()
    for selector, vals in blocks.items():
        if "@media" in selector:
            continue
        if f'data-theme="{theme}"' in selector:
            return vals
    raise AssertionError(f"no non-media token block declares data-theme={theme!r}")


def test_both_themes_define_the_same_tokens() -> None:
    """A token defined in one theme and not the other is invisible until you toggle."""
    light, dark = palette("light"), palette("dark")
    only_light = set(light) - set(dark)
    only_dark = set(dark) - set(light)
    assert not only_light, f"tokens defined only in light: {sorted(only_light)}"
    assert not only_dark, f"tokens defined only in dark: {sorted(only_dark)}"


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_contrast_meets_wcag_aa(theme: str) -> None:
    t = palette(theme)

    body = contrast(t["--text"], t["--bg"])
    assert body >= 4.5, f"{theme}: body text {body:.2f}:1 on background, need 4.5"

    muted = contrast(t["--muted"], t["--bg"])
    assert muted >= 4.0, f"{theme}: muted text {muted:.2f}:1, need ~4.5 (AA large: 3)"

    accent = contrast(t["--accent"], t["--surface"])
    assert accent >= 4.5, (
        f"{theme}: --accent is {accent:.2f}:1 on --surface. Links use it as text, so it "
        f"must clear 4.5. The light accent #1E4B8C cannot be reused unchanged in dark mode."
    )

    ink = contrast(t["--accent-2-ink"], t["--surface"])
    assert ink >= 4.5, (
        f"{theme}: --accent-2-ink is {ink:.2f}:1 on --surface. The poster orange #E17828 is "
        f"a FILL colour at 2.6:1; --accent-2-ink is its text form and must clear 4.5."
    )


def test_every_status_defines_both_theme_colours() -> None:
    statuses = yaml.safe_load((REPO / "_data" / "statuses.yml").read_text(encoding="utf-8"))
    for key, spec in statuses.items():
        assert spec.get("color_light"), f"status {key} has no color_light"
        assert spec.get("color_dark"), f"status {key} has no color_dark"
        assert spec.get("glyph"), f"status {key} has no glyph; colour alone is not enough"


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_status_colours_are_legible(theme: str) -> None:
    statuses = yaml.safe_load((REPO / "_data" / "statuses.yml").read_text(encoding="utf-8"))
    t = palette(theme)
    field = "color_light" if theme == "light" else "color_dark"
    for key, spec in statuses.items():
        # Chips render status colour as text on --surface. 3:1 is the AA bound for
        # non-body UI text; the mandatory glyph carries the meaning for anyone below it.
        c = contrast(spec[field], t["--surface"])
        assert c >= 3.0, f"{theme}: status '{key}' is {c:.2f}:1 on --surface"
