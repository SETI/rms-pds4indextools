"""Skeleton-only smoke tests for the package layout and packaged data.

These verify that the installed package imports, exposes a version, and
ships its PEP 561 marker plus the two packaged template files.
"""

import importlib.resources

import pds4indextools


def test_package_imports() -> None:
    """The package imports and exposes a truthy ``__version__``."""
    assert pds4indextools.__version__


def test_py_typed_marker_present() -> None:
    """The PEP 561 ``py.typed`` marker is packaged."""
    marker = importlib.resources.files('pds4indextools').joinpath('py.typed')
    assert marker.is_file()


def test_default_config_packaged() -> None:
    """The default config YAML is packaged under ``templates/``."""
    resource = importlib.resources.files('pds4indextools').joinpath('templates/default_config.yaml')
    assert resource.is_file()


def test_label_template_packaged() -> None:
    """The index label template is packaged under ``templates/``."""
    resource = importlib.resources.files('pds4indextools').joinpath(
        'templates/index_label_template.xml'
    )
    assert resource.is_file()
