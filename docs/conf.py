import sys
from importlib.metadata import version as _pkg_version
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

project = "fatsecret"
copyright = "2026"
release = _pkg_version("fatsecret")
version = ".".join(release.split(".")[:2])

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.doctest",
    "sphinx.ext.viewcode",
]

exclude_patterns = ["_build"]
add_module_names = False

html_theme = "sphinx_rtd_theme"
