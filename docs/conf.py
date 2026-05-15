import os
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
templates_path = ["_templates"]

html_theme = "sphinx_rtd_theme"

# Wrap signatures longer than 80 chars onto multiple lines (Sphinx 7.1+).
# Generated mutator/create methods can take 20+ optional args; rendering them
# on a single line forces a horizontal scrollbar in the RTD theme.
maximum_signature_line_length = 80
python_maximum_signature_line_length = 80

# Move type hints out of the signature into the description as a Parameters
# field list.  Combined with the ``:param NAME: ...`` lines emitted by the
# codegen pipeline, this renders the per-arg descriptions alongside their
# types as a proper field table instead of a wall of inline annotations.
autodoc_typehints = "description"
autodoc_typehints_format = "short"

# Show an in-development banner only on Read the Docs branch builds
# (e.g., master/dev). Tagged version builds set VERSION_TYPE=tag and stay clean.
_is_dev_build = os.environ.get("READTHEDOCS_VERSION_TYPE") == "branch"
html_context = {"is_dev_build": _is_dev_build}
