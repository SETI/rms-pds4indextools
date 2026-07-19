"""Integrity checks for committed test fixtures."""

from tests.conftest import DATA_ROOT


def test_bom_file_starts_with_bom_bytes() -> None:
    """The ``bom`` bundle label begins with the UTF-8 BOM byte sequence."""
    bom_label = DATA_ROOT / 'bundles' / 'bom' / 'bom.lblx'
    assert bom_label.read_bytes().startswith(b'\xef\xbb\xbf')
