import re
import sys
from pathlib import Path

_root = Path(__file__).parent.parent
sys.path.insert(0, str(_root / "src"))

project = "fatsecret"
copyright = "2026"
release = re.search(r'^version = "([^"]+)"', (_root / "pyproject.toml").read_text(), re.M).group(1)
version = ".".join(release.split(".")[:2])

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.doctest",
    "sphinx.ext.viewcode",
]

# Load sphinx_multiversion's extension when it's installed so each per-tag
# build receives the `current_version` / `versions` Jinja context used by
# our `_templates/versions.html` dropdown. We import lazily so a single-
# version `make docs` build still works on machines that haven't installed
# the dev dependency yet.
try:
    import sphinx_multiversion  # noqa: F401
except ImportError:
    pass
else:
    extensions.append("sphinx_multiversion")

exclude_patterns = ["_build"]
add_module_names = False

html_theme = "sphinx_rtd_theme"

# -- sphinx-multiversion configuration ---------------------------------------
# Only build docs for stable release tags (vMAJOR.MINOR.PATCH) and the master
# branch. Older 0.x tags (v0.2.3..v0.12.0) used a pre-OAS docs layout
# (api_docs.rst / contents.rst.inc) and an older source tree that cannot be
# imported under the current Python 3.11 / dependency floor; they are therefore
# excluded. The minimum supported tag is v0.13.0, which is the first release
# whose docs/ tree matches the current single-page api.rst layout.
smv_tag_whitelist = r"^v(0\.(1[3-9]|[2-9]\d)|[1-9]\d*\.\d+)\.\d+$"
smv_branch_whitelist = r"^master$"
smv_remote_whitelist = None  # only consider local refs
smv_released_pattern = r"^refs/tags/v\d+\.\d+\.\d+$"
smv_outputdir_format = "{ref.name}"
smv_prefer_remote_refs = False

# Register our `versions.html` template so sphinx_rtd_theme's layout.html
# (which already does `{% include "versions.html" %}` at the bottom of the
# page body) picks up our version dropdown. We deliberately do NOT set
# `html_sidebars` here: the RTD theme renders the dropdown as a floating
# element from layout.html, and overriding sidebars would clobber the
# theme's built-in navigation pane.
templates_path = ["_templates"]
