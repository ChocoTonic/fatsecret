#!/usr/bin/env python3
"""Build a static archive of fatsecret docs for every released tag.

Output goes to a staging directory (default: ./legacy-staging) laid out as:

    <staging>/index.html        # top-level listing of every version
    <staging>/<tag>/index.html  # one tree per tag, served at gh-pages root

The archive is intended to be published to the `gh-pages` branch root so
URLs like `https://chocotonic.github.io/fatsecret/v1.2.1/` resolve for
every released tag.

Design goals:
  * Idempotent: re-running produces the same bytes (no timestamps in output).
  * Tolerant: every tag yields *something*, even if it's a one-line stub.
  * Hermetic: builds happen in `git worktree` checkouts under a temp dir and
    autodoc is disabled so we never import the (often Python-3.11-incompatible)
    old source trees.

Strategy hierarchy per tag:
  A) If `docs/conf.py` exists, run sphinx-build with autodoc/doctest/viewcode
     extensions stripped (-D extensions=) and version/release injected from the
     tag name. This is the preferred path.
  B) On failure (or if docs/ is missing), fall back to a generated stub page
     built from the tag's README, linking to GitHub at the tag and to PyPI.
  C) On total failure, write a minimal one-line stub.
"""

from __future__ import annotations

import argparse
import html
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

def discover_tags(repo: Path) -> list[str]:
    """Every `vX.Y.Z` tag in the repo, sorted newest-first by semver."""
    out = subprocess.check_output(
        ["git", "-C", str(repo), "tag", "--list", "--sort=-version:refname"],
        text=True,
    )
    pat = re.compile(r"^v\d+\.\d+\.\d+$")
    return [t for t in out.splitlines() if pat.match(t)]

REPO_SLUG = "ChocoTonic/fatsecret"  # for GitHub source links
PYPI_PROJECT = "fatsecret"

# Minimal Sphinx pin. Modern Sphinx builds old .rst trees fine as long as we
# disable autodoc so it never tries to import the package.
SPHINX_REQUIREMENTS = ["sphinx==7.4.7", "furo==2024.8.6"]


@dataclass
class BuildResult:
    tag: str
    strategy: str  # "sphinx", "stub-readme", "stub-minimal"
    notes: str = ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def run(cmd: list[str], cwd: Path | None = None, check: bool = True, env: dict | None = None) -> subprocess.CompletedProcess:
    print(f"  $ {' '.join(cmd)}", flush=True)
    return subprocess.run(cmd, cwd=cwd, check=check, env=env, capture_output=True, text=True)


def github_url_at_tag(tag: str) -> str:
    return f"https://github.com/{REPO_SLUG}/tree/{tag}"


def pypi_url(tag: str) -> str:
    return f"https://pypi.org/project/{PYPI_PROJECT}/{tag.lstrip('v')}/"


# ---------------------------------------------------------------------------
# Strategy A: Sphinx build with autodoc stripped
# ---------------------------------------------------------------------------


def try_sphinx_build(tag: str, worktree: Path, out_dir: Path, venv_python: Path, master_docs: Path) -> bool:
    docs_dir = worktree / "docs"
    if not (docs_dir / "conf.py").is_file():
        print(f"  [sphinx] {tag}: no docs/conf.py, skipping strategy A")
        return False

    # Hybrid build: .rst source from the tag, theme/template from master.
    # This keeps the version switcher visually consistent and lets us ship
    # theme upgrades retroactively without rewriting history. Autodoc is
    # still disabled because old tags are not importable under modern Python.
    # Nest sanitized docs inside a per-tag build dir so master's conf.py —
    # which reads `Path(__file__).parent.parent / "pyproject.toml"` — finds
    # a pyproject with the tag's version (written below).
    build_dir = worktree.parent / f"{tag}-build"
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True)
    sanitized = build_dir / "docs"
    shutil.copytree(docs_dir, sanitized)
    version_str = tag.lstrip("v")
    (build_dir / "pyproject.toml").write_text(f'version = "{version_str}"\n')
    # Empty src/ so any `sys.path.insert(_root/src)` in master conf is harmless.
    (build_dir / "src").mkdir()

    # Drop api-spec subtree if present (OpenAPI YAML; not docs source).
    api_spec = sanitized / "api-spec"
    if api_spec.exists():
        shutil.rmtree(api_spec)

    # Pull conf.py + theme assets from master so every archived version
    # renders with the *current* template. Autodoc is force-disabled via an
    # appended override below.
    master_conf = master_docs / "conf.py"
    if not master_conf.is_file():
        print(f"  [sphinx] {tag}: master conf.py not found at {master_conf}")
        return False
    shutil.copy(master_conf, sanitized / "conf.py")
    for asset in ("_templates", "_static"):
        src = master_docs / asset
        if src.is_dir():
            dst = sanitized / asset
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)

    # Append an override that runs *after* master's conf.py:
    #   - strip autodoc/doctest/viewcode so we never import old source trees
    #   - mark this build as an archive in the page title
    # (version/release come from the per-tag pyproject.toml stub above.)
    override = '''

# --- archive override (appended by scripts/build-version-docs/build.py) ---
extensions = [e for e in list(globals().get("extensions", [])) if not e.startswith("sphinx.ext.auto") and e not in ("sphinx.ext.doctest", "sphinx.ext.viewcode")]
html_title = f"fatsecret {release} (archived)"
html_show_sphinx = False
exclude_patterns = list(set(list(globals().get("exclude_patterns", [])) + ["_build", "api-spec"]))
'''
    with (sanitized / "conf.py").open("a") as fh:
        fh.write(override)

    # Some old trees have an index.rst that .. include:: contents.rst.inc which
    # tries to use autodoc directives. We let Sphinx render those as plain
    # unknown-directive warnings (non-fatal without -W).
    try:
        run(
            [
                str(venv_python),
                "-m",
                "sphinx",
                "-b",
                "html",
                "-q",  # quiet; we want minimal log noise
                str(sanitized),
                str(out_dir),
            ],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"  [sphinx] {tag}: build FAILED")
        print(e.stdout)
        print(e.stderr)
        return False

    if not (out_dir / "index.html").is_file():
        print(f"  [sphinx] {tag}: no index.html produced")
        return False
    return True


# ---------------------------------------------------------------------------
# Strategy B: README-based stub
# ---------------------------------------------------------------------------


STUB_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>fatsecret {tag} (archived docs)</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         max-width: 760px; margin: 3em auto; padding: 0 1em; line-height: 1.5; color: #222; }}
  header {{ border-bottom: 1px solid #ddd; padding-bottom: 1em; margin-bottom: 1.5em; }}
  h1 {{ margin: 0; }}
  .subtitle {{ color: #666; margin-top: 0.3em; }}
  pre, code {{ background: #f4f4f4; padding: 0.1em 0.3em; border-radius: 3px; }}
  pre {{ padding: 0.7em; overflow-x: auto; }}
  .note {{ background: #fff8d6; border-left: 3px solid #d4a017; padding: 0.8em 1em; margin: 1.5em 0; }}
  a {{ color: #0366d6; }}
</style>
</head>
<body>
<header>
  <h1>fatsecret {tag}</h1>
  <p class="subtitle">Archived documentation snapshot</p>
</header>
<div class="note">
This is a static archive page for an older release of <code>fatsecret</code>.
For current documentation see <a href="https://chocotonic.github.io/fatsecret/">chocotonic.github.io/fatsecret</a>.
This page is a frozen snapshot for a release whose docs could not be
rebuilt from source, so it links to the most useful authoritative
references for this specific version.
</div>

<h2>Resources for {tag}</h2>
<ul>
  <li><a href="{github_url}">Source tree on GitHub at {tag}</a></li>
  <li><a href="{pypi_url}">PyPI release page for {version_str}</a></li>
  <li><a href="../">Back to legacy docs index</a></li>
</ul>

<h2>README at {tag}</h2>
{readme_html}

</body>
</html>
"""


def render_readme_block(worktree: Path) -> str:
    for name in ("README.md", "README.rst", "README.txt", "README"):
        p = worktree / name
        if p.is_file():
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            return f"<pre>{html.escape(text)}</pre>"
    return "<p><em>No README was found at this tag.</em></p>"


def write_stub(tag: str, worktree: Path | None, out_dir: Path, minimal: bool = False) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    version_str = tag.lstrip("v")
    if minimal or worktree is None:
        readme_html = "<p><em>README content was not preserved for this archive entry.</em></p>"
    else:
        readme_html = render_readme_block(worktree)
    page = STUB_TEMPLATE.format(
        tag=html.escape(tag),
        github_url=html.escape(github_url_at_tag(tag)),
        pypi_url=html.escape(pypi_url(tag)),
        version_str=html.escape(version_str),
        readme_html=readme_html,
    )
    (out_dir / "index.html").write_text(page, encoding="utf-8")


# ---------------------------------------------------------------------------
# Top-level index
# ---------------------------------------------------------------------------


INDEX_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>fatsecret documentation</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         max-width: 760px; margin: 3em auto; padding: 0 1em; line-height: 1.5; color: #222; }}
  h1 {{ margin-bottom: 0.2em; }}
  .subtitle {{ color: #666; margin-top: 0; }}
  li {{ margin: 0.3em 0; }}
  .note {{ background: #eef6ff; border-left: 3px solid #0366d6; padding: 0.8em 1em; margin: 1.5em 0; }}
  code {{ background: #f4f4f4; padding: 0.1em 0.3em; border-radius: 3px; }}
</style>
</head>
<body>
<h1>fatsecret documentation</h1>
<p class="subtitle">Per-release documentation archive</p>

<div class="note">
Every released version of <code>fatsecret</code> has a permanent docs URL
at <code>https://chocotonic.github.io/fatsecret/vX.Y.Z/</code>. The list
below links to all of them, newest first. <code>latest/</code> tracks
master; <code>stable/</code> redirects to the highest released tag.
</div>

<h2>Versions</h2>
<ul>
{items}
</ul>
</body>
</html>
"""


def write_top_index(
    staging_legacy: Path,
    built: list[BuildResult],
    include_latest: bool = False,
    include_stable: bool = False,
    stable_target: str | None = None,
) -> None:
    # Sort newest-first by semver-ish key.
    def key(r: BuildResult) -> tuple:
        parts = r.tag.lstrip("v").split(".")
        return tuple(int(p) for p in parts)

    lines: list[str] = []
    if include_latest:
        lines.append(
            '  <li><a href="latest/">latest</a>'
            ' <small style="color:#888">[tracks master]</small></li>'
        )
    if include_stable:
        target_note = f" -> {html.escape(stable_target)}" if stable_target else ""
        lines.append(
            f'  <li><a href="stable/">stable</a>'
            f' <small style="color:#888">[redirect{target_note}]</small></li>'
        )
    for r in sorted(built, key=key, reverse=True):
        lines.append(
            f'  <li><a href="{html.escape(r.tag)}/">{html.escape(r.tag)}</a>'
            f' <small style="color:#888">[{html.escape(r.strategy)}]</small></li>'
        )
    items = "\n".join(lines)
    (staging_legacy / "index.html").write_text(
        INDEX_TEMPLATE.format(items=items), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# latest/ : real build from the current working tree
# ---------------------------------------------------------------------------


def build_latest(repo: Path, out_dir: Path, venv_python: Path) -> bool:
    """Build docs from the current working tree with full autodoc enabled.

    Installs the project into the same venv used by the archive (editable
    install) so autodoc/viewcode can import `fatsecret`.
    """
    docs_dir = repo / "docs"
    if not (docs_dir / "conf.py").is_file():
        print(f"  [latest] no docs/conf.py at {docs_dir}, skipping")
        return False

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Install the project into the venv so autodoc can import it.
    try:
        run([str(venv_python), "-m", "pip", "install", "--quiet", "-e", str(repo)])
    except subprocess.CalledProcessError as e:
        print(f"  [latest] failed to install project: {e.stderr}")
        return False

    try:
        run(
            [
                str(venv_python),
                "-m",
                "sphinx",
                "-b",
                "html",
                "-q",
                str(docs_dir),
                str(out_dir),
            ],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print("  [latest] sphinx build FAILED")
        print(e.stdout)
        print(e.stderr)
        return False

    if not (out_dir / "index.html").is_file():
        print("  [latest] no index.html produced")
        return False
    return True


# ---------------------------------------------------------------------------
# stable/ : tiny redirect to the highest tag
# ---------------------------------------------------------------------------


STABLE_REDIRECT_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>fatsecret stable docs</title>
<meta http-equiv="refresh" content="0; url=../{target}/">
<link rel="canonical" href="../{target}/">
</head>
<body>
<p>Redirecting to <a href="../{target}/">fatsecret {target} documentation</a>&hellip;</p>
</body>
</html>
"""


def write_stable_redirect(out_dir: Path, target_tag: str) -> None:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    page = STABLE_REDIRECT_TEMPLATE.format(target=html.escape(target_tag))
    (out_dir / "index.html").write_text(page, encoding="utf-8")


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def ensure_venv(venv_dir: Path) -> Path:
    """Create an isolated venv with Sphinx pinned. Returns the python binary."""
    if not venv_dir.exists():
        run([sys.executable, "-m", "venv", str(venv_dir)])
    py = venv_dir / "bin" / "python"
    run([str(py), "-m", "pip", "install", "--quiet", "--upgrade", "pip"])
    run([str(py), "-m", "pip", "install", "--quiet", *SPHINX_REQUIREMENTS])
    return py


def add_worktree(repo: Path, tag: str, dest: Path) -> None:
    if dest.exists():
        # Reuse if already populated for the right tag; otherwise nuke.
        shutil.rmtree(dest)
    run(["git", "worktree", "add", "--detach", str(dest), tag], cwd=repo)


def remove_worktree(repo: Path, dest: Path) -> None:
    try:
        run(["git", "worktree", "remove", "--force", str(dest)], cwd=repo, check=False)
    except Exception:
        pass
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)


def build_tag(tag: str, repo: Path, work_root: Path, staging_legacy: Path, venv_python: Path, master_docs: Path) -> BuildResult:
    print(f"\n== Building {tag} ==")
    worktree = work_root / tag
    out_dir = staging_legacy / tag
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        add_worktree(repo, tag, worktree)
    except subprocess.CalledProcessError as e:
        print(f"  worktree add failed: {e.stderr}")
        write_stub(tag, None, out_dir, minimal=True)
        return BuildResult(tag, "stub-minimal", "worktree add failed")

    try:
        if try_sphinx_build(tag, worktree, out_dir, venv_python, master_docs):
            return BuildResult(tag, "sphinx")

        print(f"  [stub] {tag}: falling back to README-based stub")
        write_stub(tag, worktree, out_dir, minimal=False)
        return BuildResult(tag, "stub-readme")
    except Exception as e:  # noqa: BLE001
        print(f"  unexpected error for {tag}: {e!r}")
        write_stub(tag, worktree if worktree.exists() else None, out_dir, minimal=worktree is None)
        return BuildResult(tag, "stub-minimal", repr(e))
    finally:
        remove_worktree(repo, worktree)
        build_dir = work_root / f"{tag}-build"
        if build_dir.exists():
            shutil.rmtree(build_dir, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--staging", type=Path, default=Path("legacy-staging").resolve())
    parser.add_argument(
        "--master-docs",
        type=Path,
        default=None,
        help="Path to docs/ dir whose conf.py and theme assets override every "
        "tag's. Defaults to <repo>/docs.",
    )
    parser.add_argument("--work-root", type=Path, default=Path(tempfile.gettempdir()) / "fatsecret-legacy-worktrees")
    parser.add_argument(
        "--tags",
        nargs="*",
        default=None,
        help="Tag list. Defaults to every `vX.Y.Z` tag the repo currently carries.",
    )
    parser.add_argument(
        "--build-current",
        action="store_true",
        help="Additionally build <staging>/latest/ from the working tree and "
        "write a redirect at <staging>/stable/ pointing to the highest tag.",
    )
    parser.add_argument(
        "--only-current",
        action="store_true",
        help="Skip tag builds entirely; only build latest/ and stable/. Useful "
        "for refreshing latest/ on master pushes. Implies --build-current.",
    )
    args = parser.parse_args()

    repo: Path = args.repo.resolve()
    staging: Path = args.staging.resolve()
    work_root: Path = args.work_root.resolve()
    master_docs: Path = (args.master_docs or (repo / "docs")).resolve()
    build_current = args.build_current or args.only_current

    all_tags = discover_tags(repo)
    if args.only_current:
        tags: list[str] = []
    else:
        tags = args.tags if args.tags is not None else all_tags
        if not tags:
            print("No vX.Y.Z tags discovered in repo.", file=sys.stderr)
            return 1
    if tags:
        print(f"Building {len(tags)} tags: {' '.join(tags)}")
    else:
        print("Skipping tag builds (--only-current).")

    # Each tag's docs land at <staging>/<tag>/ directly — no `legacy/`
    # prefix. The publish step uploads <staging>/ as the gh-pages root, so
    # the final URL is `https://chocotonic.github.io/fatsecret/vX.Y.Z/`.
    staging.mkdir(parents=True, exist_ok=True)
    work_root.mkdir(parents=True, exist_ok=True)

    venv_dir = work_root / ".venv"
    venv_python = ensure_venv(venv_dir)

    results: list[BuildResult] = []
    for tag in tags:
        results.append(build_tag(tag, repo, work_root, staging, venv_python, master_docs))

    latest_ok = False
    stable_target: str | None = None
    if build_current:
        print("\n== Building latest/ from working tree ==")
        latest_ok = build_latest(repo, staging / "latest", venv_python)

        # Pick the highest tag for stable. all_tags is sorted newest-first by
        # semver via `git tag --sort=-version:refname`.
        if all_tags:
            stable_target = all_tags[0]
            print(f"\n== Writing stable/ redirect -> {stable_target} ==")
            write_stable_redirect(staging / "stable", stable_target)
        else:
            print("\n== Skipping stable/: no vX.Y.Z tags found ==")

    # Only rewrite the top index when we're doing a full refresh or building
    # current entries; otherwise an incremental tag publish (keep_files=true)
    # would clobber existing latest/stable links with a partial index.
    if args.only_current:
        # Don't touch the top index — it's already published with the full
        # tag listing. We only refresh latest/.
        pass
    else:
        write_top_index(
            staging,
            results,
            include_latest=build_current and latest_ok,
            include_stable=build_current and stable_target is not None,
            stable_target=stable_target,
        )

    print("\n== Summary ==")
    for r in results:
        extra = f"  ({r.notes})" if r.notes else ""
        print(f"  {r.tag:10s}  {r.strategy}{extra}")
    if build_current:
        print(f"  {'latest':10s}  {'sphinx' if latest_ok else 'FAILED'}")
        if stable_target:
            print(f"  {'stable':10s}  redirect -> {stable_target}")
    print(f"\nOutput: {staging}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
