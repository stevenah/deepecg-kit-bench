"""Theme correctness, asserted mechanically.

Two properties, both of which are easy to break by hand and impossible to notice in one
theme while working in the other:

1. Every colour is defined in a token block, and no literal hex leaks into a rule. A stray
   hex looks fine in whichever theme you authored it in and wrong in the other.
2. Both palettes meet WCAG AA contrast. #1E4B8C is 7.9:1 on the light surface and about
   2:1 on the dark background -- reusing it unchanged would be a real accessibility
   failure, not a cosmetic one.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
CSS = REPO / "site" / "style.css"
HEX = re.compile(r"#[0-9a-fA-F]{6}\b")
TOKEN_BLOCK = r"(:root[^{]*|@media[^{]*\{\s*:root[^{]*)\{([^}]*)\}"


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
    for m in re.finditer(TOKEN_BLOCK, text):
        selector = " ".join(m.group(1).split())
        vals = dict(re.findall(r"(--[\w-]+)\s*:\s*(#[0-9a-fA-F]{6})\s*;", m.group(2)))
        if vals:
            blocks.setdefault(selector, {}).update(vals)
    return blocks


def palette(theme: str) -> dict[str, str]:
    """Tokens for one theme, found by selector content rather than by position.

    Which theme owns bare `:root` is a design decision that has already changed once
    (light-default -> dark-default, to match ECGBench). The test must not encode it.
    """
    for selector, vals in token_blocks().items():
        if "@media" not in selector and f'data-theme="{theme}"' in selector:
            return vals
    raise AssertionError(f"no non-media token block declares data-theme={theme!r}")


def test_every_hex_lives_in_a_token_block() -> None:
    """No literal colour outside a :root declaration."""
    text = CSS.read_text(encoding="utf-8")
    # Comments first: a colour NAMED in prose is documentation, not a leak.
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    # Then blank out every :root / @media-:root block; any remaining hex is a real leak.
    leaks = HEX.findall(re.sub(TOKEN_BLOCK, "", text))
    assert not leaks, f"literal hex outside the token blocks: {sorted(set(leaks))}"


def test_both_themes_define_the_same_tokens() -> None:
    """A token defined in one theme and not the other is invisible until you toggle."""
    light, dark = palette("light"), palette("dark")
    assert not set(light) - set(dark), f"tokens defined only in light: {sorted(set(light) - set(dark))}"
    assert not set(dark) - set(light), f"tokens defined only in dark: {sorted(set(dark) - set(light))}"


def test_system_light_matches_the_light_theme() -> None:
    """Auto mode on a light system must be the light theme, not a third palette."""
    media = next(v for s, v in token_blocks().items() if "@media" in s)
    assert media == palette("light")


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_contrast_meets_wcag_aa(theme: str) -> None:
    t = palette(theme)
    pairs = [
        ("--text", "--bg", 4.5, "body text"),
        ("--text", "--surface", 4.5, "text in an open panel"),
        ("--muted", "--bg", 4.5, "secondary text"),
        ("--muted", "--surface", 4.5, "secondary text in an open panel"),
        ("--muted", "--surface-2", 4.5, "column headers"),
        ("--accent", "--bg", 4.5, "links"),
        ("--accent", "--surface", 4.5, "links in an open panel"),
        ("--warn", "--bg", 4.5, "note markers"),
        ("--warn", "--surface", 4.5, "the zero-prediction note in a panel"),
        ("--plot-ink", "--plot-card", 4.5, "plot captions"),
        ("--accent2", "--bg", 4.5, "the version tag and Quick Start links"),
        ("--danger", "--bg", 4.5, "the Report an Issue link"),
        ("--code-ink", "--code-bg", 4.5, "code"),
        ("--code-comment", "--code-bg", 4.5, "code comments"),
        ("--code-keyword", "--code-bg", 4.5, "code keywords"),
        ("--code-string", "--code-bg", 4.5, "code strings"),
        ("--code-func", "--code-bg", 4.5, "code function names"),
        ("--code-number", "--code-bg", 4.5, "code numbers"),
    ]
    for ink, ground, bound, what in pairs:
        ratio = contrast(t[ink], t[ground])
        assert ratio >= bound, f"{theme}: {what} ({ink} on {ground}) is {ratio:.2f}:1, need {bound}"
