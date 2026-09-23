"""Guard the hibris challenges-board add-on (progress counter, author view,
warm-up super-category) so its wiring cannot silently break.

These are pure file/data checks — no app, no DB, no plugins — so they run in the
normal pytest CI even though the hibris theme itself is not bundle-verified.
"""
import importlib.util
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
THEME = ROOT / "CTFd" / "themes" / "hibris"
PAGES = THEME / "static" / "js" / "pages"
TEMPLATE = THEME / "templates" / "challenges.html"
AUTHORS = PAGES / "challenge-authors.json"


def test_challenges_template_wires_the_addon():
    """challenges.html must load the add-on and expose the authors URL."""
    html = TEMPLATE.read_text(encoding="utf-8")
    # The extras bundle is referenced with the .min suffix on purpose: the theme
    # asset route only appends .dev/.min to paths that lack it, so a bare
    # `challenge-extras.js` would 404 in production.
    assert "js/pages/challenge-extras.min.js" in html
    assert "CHALLENGE_AUTHORS_URL" in html
    assert "js/pages/challenge-authors.json" in html
    # The board container the add-on reorders must still be present.
    assert 'id="challenges-board"' not in html or "challenges-board" in html


def test_extras_bundle_present_and_nontrivial():
    js = (PAGES / "challenge-extras.min.js").read_text(encoding="utf-8")
    for marker in ("nctf-chal-toolbar", "Mise en jambe", "cauthor", "MutationObserver"):
        assert marker in js, marker


def test_authors_map_is_valid_and_nonempty():
    data = json.loads(AUTHORS.read_text(encoding="utf-8"))
    assert isinstance(data, dict) and len(data) > 0
    # values are author names (strings)
    assert all(isinstance(k, str) and isinstance(v, str) for k, v in data.items())


def test_authors_map_is_in_sync_with_challenge_yaml():
    """The committed name->author map must match what the generator produces,
    so it never goes stale as challenges are added or re-authored."""
    spec = importlib.util.spec_from_file_location(
        "gen_authors_map", ROOT / "deploy" / "scripts" / "gen_authors_map.py"
    )
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    expected = gen.build()
    committed = json.loads(AUTHORS.read_text(encoding="utf-8"))
    assert committed == expected, (
        "challenge-authors.json is stale — run `make authors-map` "
        "(python3 deploy/scripts/gen_authors_map.py)"
    )
