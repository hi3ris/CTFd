"""deploy/scripts/publish_writeups.py -- pure assembly (no network) and the
draft/publish flow against the real Pages API and renderer."""
import importlib.util
import pathlib

from CTFd.utils import set_config
from CTFd.utils.security.auth import generate_user_token
from tests.helpers import create_ctfd, destroy_ctfd, setup_ctfd

_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "deploy"
    / "scripts"
    / "publish_writeups.py"
)
_spec = importlib.util.spec_from_file_location("publish_writeups", _PATH)
pw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pw)

README = """# flask-unsign -- solution

**Summary:** re-sign the cookie.

## Steps

```
# not a heading, a comment in a code block
python3 solve.py  # prints NCTF{itsdangerous_secret_key_resign_admin_session}
```

## Flag

NCTF{itsdangerous_secret_key_resign_admin_session} and the format is NCTF{...}
"""


def tree(tmp_path):
    root = tmp_path / "challenges"
    for cat, slug, name, flags, author, readme in [
        (
            "web",
            "flask-unsign",
            "flask-unsign",
            ["NCTF{itsdangerous_secret_key_resign_admin_session}"],
            "dagbanjaphet",
            README,
        ),
        (
            "web",
            "jwt-cousin",
            "jwt-cousin",
            None,
            "ctf-2026",
            "# jwt\n\nteam flag NCTF{" + "x" * 20 + "}\n",
        ),
        ("pwn", "heap-note", "heap-note", ["NCTF{heap}"], "", None),
    ]:
        d = root / cat / slug
        (d / "solution").mkdir(parents=True)
        y = f"name: {name}\ncategory: {cat}\nvalue: 150\nauthor: {author}\n"
        if flags:
            y += "flags:\n" + "".join(f"  - {f}\n" for f in flags)
        else:
            y += "flags:\n  - type: team_hmac\n    content: web-jwt\n"
        (d / "challenge.yml").write_text(y)
        if readme:
            (d / "solution" / "README.md").write_text(readme)
        (d / "solution" / "solve.py").write_text("print('never published')\n")
    return root


def test_redact_exact_then_generic_keeps_placeholders():
    out = pw.redact(README, ["NCTF{itsdangerous_secret_key_resign_admin_session}"])
    assert "itsdangerous" not in out
    assert out.count(pw.PLACEHOLDER) == 2
    assert "NCTF{...}" in out  # the format hint survives
    assert pw.redact("NCTF{…} NCTF{} NCTF{real_one}") == "NCTF{…} NCTF{} NCTF{…}"


def test_shift_headings_skips_fenced_code():
    out = pw.shift_headings(README, 2)
    assert out.startswith("### flask-unsign")
    assert "#### Steps" in out and "#### Flag" in out
    assert "# not a heading, a comment in a code block" in out
    assert (
        pw.shift_headings("##### deep\n###### deeper\n", 2)
        == "###### deep\n###### deeper\n"
    )


def test_build_pages_index_and_categories(tmp_path):
    items = pw.load_challenges(tree(tmp_path))
    assert [c["slug"] for c in items] == ["heap-note", "flask-unsign", "jwt-cousin"]
    pages = pw.build_pages(items, ctf_name="NCTF26")
    assert [p["route"] for p in pages] == ["writeups", "writeups/pwn", "writeups/web"]
    index, pwn, web = pages
    assert index["menu"] and not web["menu"]
    assert "**3 challenges**, **2 catégories**" in index["content"]
    assert "[writeup](/writeups/web#flask-unsign)" in index["content"]
    assert "| `heap-note` | 150 |  | _pas de writeup_ |" in index["content"]
    assert "dagbanjaphet" in index["content"]
    assert '<a id="flask-unsign"></a>' in web["content"]
    assert "### flask-unsign -- solution" in web["content"]
    assert "itsdangerous_secret_key" not in web["content"]
    assert "NCTF{xxxxxxxxxxxxxxxxxxxx}" not in web["content"]  # generic layer
    assert "never published" not in web["content"]
    assert "_Pas de writeup publié" in pwn["content"]
    # category filter
    only = pw.load_challenges(tree(tmp_path / "b"), {"pwn"})
    assert [c["category"] for c in only] == ["pwn"]


def test_page_size_guard(tmp_path, monkeypatch):
    items = pw.load_challenges(tree(tmp_path))
    monkeypatch.setattr(pw, "MAX_PAGE_BYTES", 100)
    try:
        pw.build_pages(items)
    except SystemExit as e:
        assert "64 Ko" in str(e)
    else:
        raise AssertionError("a page over the MariaDB TEXT limit must be refused")


def test_may_publish_only_after_end():
    assert not pw.may_publish("", now=100)
    assert not pw.may_publish(None, now=100)
    assert not pw.may_publish("200", now=100)
    assert pw.may_publish("100", now=100)
    assert pw.may_publish("50", now=100)
    assert pw.may_publish("200", now=100, force=True)
    assert not pw.may_publish("garbage", now=100)


def test_static_render_links_and_anchors(tmp_path):
    pages = pw.build_pages(pw.load_challenges(tree(tmp_path)))
    files = pw.write_static(pages, tmp_path / "out")
    assert [pathlib.Path(f).name for f in files] == [
        "index.html",
        "pwn.html",
        "web.html",
    ]
    index = (tmp_path / "out" / "index.html").read_text()
    assert 'href="web.html#flask-unsign"' in index and "/writeups" not in index
    web = (tmp_path / "out" / "web.html").read_text()
    assert '<a id="flask-unsign"></a>' in web and "<h3>flask-unsign" in web
    assert 'href="index.html"' in web


class _Client:
    """publish_writeups.Ctfd over the Flask test client (admin API token)."""

    def __init__(self, client, token):
        self.client = client
        self.url = ""
        self.h = {"Authorization": f"Token {token}", "Content-Type": "application/json"}

    def call(self, method, path, body=None):
        r = self.client.open(path, method=method, json=body, headers=self.h)
        assert r.status_code == 200, (
            method,
            path,
            r.status_code,
            r.get_data(as_text=True)[:200],
        )
        return r.get_json()

    pages = pw.Ctfd.pages
    config = pw.Ctfd.config


def test_prepare_then_publish_against_ctfd(tmp_path):
    app = create_ctfd(enable_plugins=True, setup=False)
    app = setup_ctfd(app, user_mode="teams", ctf_theme="hibris", ctf_name="NCTF26")
    with app.app_context():
        from CTFd.models import Users

        token = generate_user_token(Users.query.get(1)).value
        pages = pw.build_pages(pw.load_challenges(tree(tmp_path)), ctf_name="NCTF26")
        with app.test_client() as anon:
            api = _Client(app.test_client(), token)
            pw.upsert(api, pages, draft=True)
            pw.upsert(api, pages, draft=True)  # idempotent (PATCH, no duplicate route)
            assert len(api.pages()) == 1 + 3  # index page of the CTF + ours
            assert anon.get("/writeups").status_code == 404
            assert anon.get("/writeups/web").status_code == 404
            # The published-writeups Page menu item ("Writeups NCTF26", see below)
            # must not appear before publishing. Check that exact label, not the
            # bare word "Writeups" -- the in-app writeups plugin registers its own
            # "Writeups" nav item, which is always present and unrelated here.
            assert "Writeups NCTF26" not in anon.get("/").get_data(as_text=True)

            set_config("end", "4102444800")  # 2100: not ended
            assert not pw.may_publish(api.config("end"))
            set_config("end", "1")
            assert pw.may_publish(api.config("end"))
            pw.upsert(api, pages, draft=False)

            r = anon.get("/writeups")
            assert r.status_code == 200
            body = r.get_data(as_text=True)
            assert "<table>" in body and 'href="/writeups/web#flask-unsign"' in body
            assert "Writeups NCTF26" in anon.get("/").get_data(
                as_text=True
            )  # in the menu
            r = anon.get("/writeups/web")
            body = r.get_data(as_text=True)
            assert r.status_code == 200
            assert '<a id="flask-unsign"></a>' in body
            assert "<h3>flask-unsign -- solution</h3>" in body
            assert "itsdangerous_secret_key" not in body
            assert "NCTF{…}" in body  # safe_format left the placeholder alone

            pw.set_draft(api, pages, True)
            assert anon.get("/writeups").status_code == 404
    destroy_ctfd(app)
