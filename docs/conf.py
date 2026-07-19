#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Configuration file for the Sphinx documentation builder.

# -- Path setup --------------------------------------------------------------

import importlib.metadata
import os
import sys
sys.path.insert(0, os.path.abspath('../src'))

# Verify the source path exists
if not os.path.exists(os.path.abspath('../src')):
    import warnings
    warnings.warn("Source directory '../src' not found. API documentation may be incomplete.")

# -- Project information -----------------------------------------------------

project = 'rms-pds4indextools'
copyright = '2025, SETI Institute'
author = 'SETI Institute'

# The full version, including alpha/beta/rc tags
try:
    release = importlib.metadata.version('rms-pds4indextools')
except importlib.metadata.PackageNotFoundError:
    release = '1.0.0'  # fallback for development

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'sphinxcontrib.mermaid',
    'myst_parser',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# CONTRIBUTING.md is split in contributing.rst; the tail fragment starts at
# "## ..." so MyST reports a false-positive heading-level warning.
suppress_warnings = ['myst.header']

# The suffix(es) of source filenames.
source_suffix = ['.rst', '.md']

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.
html_theme = 'sphinx_rtd_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
# html_static_path = ['_static']

add_module_names = False
autodoc_typehints_format = "short"

# -- Extension configuration -------------------------------------------------

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = False
napoleon_type_aliases = None
napoleon_attr_annotations = True

# Intersphinx settings
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'lxml': ('https://lxml.de/apidoc/', None),
    'pydantic': ('https://docs.pydantic.dev/latest/', None),
    'requests': ('https://requests.readthedocs.io/en/latest/', None),
}

# MyST-Parser settings
myst_enable_extensions = [
    "colon_fence",
    "deflist",
]

# Mermaid settings — use client-side rendering so no mmdc binary is required
# in CI or on ReadTheDocs.
mermaid_output_format = 'raw'

# Third-party types that publish no Sphinx inventory, plus autodoc-rendered
# type-alias/annotation fragments that nitpicky mode cannot resolve. Only
# non-pds4indextools targets are listed; every pds4indextools.* symbol must
# resolve for real (see Appendix C.1).
nitpick_ignore = [
    # PdsTemplate types are not documented externally; skip in nitpicky mode.
    ('py:class', 'pdstemplate.PdsTemplate'),
    # pydantic internals have no cross-referenceable inventory entries.
    ('py:class', 'pydantic.main.BaseModel'),
    ('py:class', 'pydantic.functional_validators.AfterValidator'),
    # lxml element type used in scraper annotations.
    ('py:class', 'lxml.etree._Element'),
    # tqdm progress-bar type used in logging annotations.
    ('py:class', 'tqdm.tqdm'),
    ('py:class', 'tqdm.std.tqdm'),
    # autodoc splits complex subscripted annotations on commas, producing
    # these unresolvable fragments from the AbsolutePath and Literal aliases.
    ('py:obj', "typing.Annotated[~pathlib.Path"),
    ('py:obj', "typing.Literal['LF'"),
    ('py:class', 'dict[str'),
    # Autodoc expands the AbsolutePath pydantic alias in IndexConfig's
    # xsd_cache_dir annotation and emits a py:class xref to its private
    # AfterValidator function. This is a rendering artifact of the alias
    # expansion, not a missing public-API doc; the public AbsolutePath alias
    # itself is documented in module.rst.
    ('py:class', 'pds4indextools.config._require_absolute'),
]
