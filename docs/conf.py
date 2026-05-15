import os
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

exclude_patterns = ["_build"]
add_module_names = False
templates_path = ["_templates"]

html_theme = "sphinx_rtd_theme"

# Show an in-development banner only on Read the Docs branch builds
# (e.g., master/dev). Tagged version builds set VERSION_TYPE=tag and stay clean.
_is_dev_build = os.environ.get("READTHEDOCS_VERSION_TYPE") == "branch"
html_context = {"is_dev_build": _is_dev_build}
