"""Guard the hibris « Fonds vivants » layer (js/nctf-fx.js): the storm wired to
the first-blood feed, the scoreboard radar, the auth circuit, the error-page
cipher rain and the static-page aurora.

Pure file checks, like test_hibris_challenges_board: hibris has no build
pipeline, so the .min and .dev files must stay the same file, and the event
wiring lives in templates that a refactor could silently drop.
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
THEME = ROOT / "CTFd" / "themes" / "hibris"
BASE = (THEME / "templates" / "base.html").read_text(encoding="utf-8")
SCOREBOARD = (THEME / "templates" / "scoreboard.html").read_text(encoding="utf-8")
JS_MIN = THEME / "static" / "js" / "nctf-fx.min.js"
JS_DEV = THEME / "static" / "js" / "nctf-fx.dev.js"
CSS_MIN = THEME / "static" / "css" / "nctf-fx.min.css"
CSS_DEV = THEME / "static" / "css" / "nctf-fx.dev.css"


def test_min_and_dev_are_the_same_file():
    assert JS_MIN.read_bytes() == JS_DEV.read_bytes()
    assert CSS_MIN.read_bytes() == CSS_DEV.read_bytes()


def test_base_loads_the_layer():
    # suffix-less on purpose: the theme route appends .min/.dev itself
    assert "path='css/nctf-fx.css'" in BASE
    assert "path='js/nctf-fx.js'" in BASE


def test_first_blood_feed_reaches_the_storm():
    """The HUD poll broadcasts a NEW first blood (not the one already there on
    page load), and the SSE toast triggers an early re-poll instead of a second
    event stream."""
    m = re.search(
        r"if \(fbLast !== null && fbLast !== d\.solve_id\) \{(.*?)\n\s*\}", BASE, re.S
    )
    assert m, "the HUD first-blood change detection moved; update this test"
    assert 'new CustomEvent("nctf:firstblood"' in m.group(1)
    assert "ezq--notifications-toast-container" in BASE
    # ezToast creates the container and inserts the first toast in one go:
    # the toasts already inside must be checked, not only later additions.
    assert "Array.prototype.forEach.call(box.children, onToast)" in BASE
    assert "new EventSource" not in BASE

    js = JS_MIN.read_text(encoding="utf-8")
    assert '"nctf:firstblood"' in js
    # the tile is found by the challenge id the /recent feed carries
    assert 'button.challenge-button[value="' in js
    assert "challenge_id" in js


def test_scoreboard_feeds_the_radar():
    assert 'new CustomEvent("nctf:score"' in SCOREBOARD
    assert '"nctf:score"' in JS_MIN.read_text(encoding="utf-8")


def test_safety_rails():
    js = JS_MIN.read_text(encoding="utf-8")
    css = CSS_MIN.read_text(encoding="utf-8")
    assert "prefers-reduced-motion" in js and "prefers-reduced-motion" in css
    assert "visibilitychange" in js
    # ≤ 3 flashes per second (WCAG 2.3.1): strikes are queued 400 ms apart
    assert "400 - (performance.now() - lastStrike)" in js
    # layers never sit above the content nor catch clicks
    block = re.search(r"\.nctf-fx\s*\{([^}]*)\}", css).group(1)
    assert "z-index: -1" in block and "pointer-events: none" in block


def test_one_animated_background_per_page():
    js = JS_MIN.read_text(encoding="utf-8")
    router = js[js.index("AIGUILLAGE") :]
    for fn in ("storm(board)", "radar()", "circuit(", "cipher()", "aurora()"):
        assert fn in router, fn
    # an if / else-if chain: exactly one layer is picked
    assert router.count("} else if (") == 4


def test_tokens_the_layer_reads_are_defined():
    root = re.search(r":root\s*\{(.*?)\}", BASE, re.S).group(1)
    for name in (
        "--red-text",
        "--gold",
        "--bolt-core",
        "--flash",
        "--aurora-green",
        "--aurora-yellow",
        "--aurora-red",
        "--cipher",
    ):
        assert name + ":" in root, name


# --------------------------------------------------------------------------
# Grand Prix v2 (scoreboard.html)
# --------------------------------------------------------------------------
def test_race_positions_by_score_and_never_clips():
    """A kart sits at score / leader score, anchored by its LEFT edge between
    the rank badge and a reserve before the finish line: the old centred
    translate(-50%) clipped trailing karts on phones (audit finding)."""
    assert "var(--p, 0) * (100% - var(--start, 56px) - var(--reserve" in SCOREBOARD
    assert "transform:translate(-50%,-50%)" not in SCOREBOARD
    assert 'setProperty("--p"' in SCOREBOARD


def test_race_features_are_wired():
    for needle in (
        # gaps in points + « à 1 flag » from the median challenge value
        "à 1 flag",
        "flagStep",
        # 1 h trend, 30 min ghost, categories: from the public top-N history
        "/api/v1/scoreboard/top/",
        "ref - 3600e3",
        "ref - 1800e3",
        "cat-chips",
        # commentator, announced politely to screen readers
        'id="rc-comment" role="log" aria-live="polite"',
        # freeze fog and the organiser-driven final reveal (?big=1&reveal=1, R)
        "fogged",
        "reveal=1",
        'e.key === "r"',
        "nctf:kartstrike",
        # explorable pack + duel
        "togglePack",
        "renderPack",
        "pickDuel",
        "drawDuelChart",
        # lanes carry their account for the kart lightning
        'setAttribute("data-account"',
    ):
        assert needle in SCOREBOARD, needle


def test_race_first_bloods_strike_the_kart_once():
    js = JS_MIN.read_text(encoding="utf-8")
    assert "nctf-front" in js and '.car-lane[data-account="' in js
    assert '"nctf:kartstrike"' in js
    # the HUD and the race may both report the same first blood
    assert "freshFb(d)" in js
    assert 'fire("nctf:firstblood", d)' in SCOREBOARD


def test_race_duel_palette_is_the_validated_pair():
    # validated with the dataviz palette checker on --panel (#0b0f18), dark mode
    assert 'var DUEL_COL = ["#b38a00", "#5b8fe8"]' in SCOREBOARD


def test_race_motion_is_guarded():
    assert "if (reducedMotion()){ revealDone = true;" in SCOREBOARD
    block = SCOREBOARD[SCOREBOARD.rindex("@media (prefers-reduced-motion: reduce)") :]
    for sel in (".track.fogged .fog", ".rc-comment li:first-child", ".track.revealing"):
        assert sel in block, sel
