import re
import sys
from pathlib import Path

_root = Path(__file__).parent.parent
sys.path.insert(0, str(_root / "src"))
sys.path.insert(0, str(_root / "docs" / "_ext"))
sys.path.insert(0, str(_root / "docs" / "_ext"))

project = "fatsecret"
copyright = "2026"
release = re.search(r'^version = "([^"]+)"', (_root / "pyproject.toml").read_text(), re.M).group(1)
version = ".".join(release.split(".")[:2])

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.doctest",
    "sphinx.ext.viewcode",
    "fatsecret_oas",
]

exclude_patterns = ["_build"]
add_module_names = False

html_theme = "sphinx_rtd_theme"
