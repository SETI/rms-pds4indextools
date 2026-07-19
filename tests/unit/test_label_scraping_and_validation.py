"""Unit tests for :mod:`pds4indextools.scraper` (Phase 7).

Exercises the label-scraping and validation package end to end through its
two public names, :class:`~pds4indextools.scraper.ScrapeResult` and
:func:`~pds4indextools.scraper.scrape_label`, covering spec section 8
(R-LID-001/010/020, R-FS-010), section 9 (R-PARSE-*, R-SCRAPE-*, R-VAL-*),
section 10 (R-XP-013, R-XP-020), and section 12 (R-NIL-*, R-MISS-*).

Every temporary label a test writes uses the ``.lblx`` suffix (owner
decision #1), except the ``filespec`` byte-length rows, whose whole point is
an exact path byte count and therefore build arbitrary-length names. The
schema resolver is a typed stub subclass so the tests never touch the
network; ``nillable_config`` is a hand-built mapping mirroring the default
config's ``nillable`` section.
"""

from collections.abc import Mapping
from pathlib import Path

import pytest
from lxml import etree

from pds4indextools.config import NillableEntry
from pds4indextools.errors import (
    LabelError,
    LidError,
    NilError,
    ParseError,
    ScrapedValueError,
)
from pds4indextools.schema_types import SchemaTypeResolver
from pds4indextools.scraper import ScrapeResult, scrape_label

NS_PDS = 'http://pds.nasa.gov/pds4/pds/v1'
NS_XSI = 'http://www.w3.org/2001/XMLSchema-instance'
NS_GEOM = 'http://pds.nasa.gov/pds4/geom/v1'

DEFAULT_LID = 'urn:nasa:pds:test_simple:index:row1'
SCHEMA_LOC = f'{NS_PDS} https://pds.nasa.gov/pds4/pds/v1/PDS4_PDS_1L00.xsd'

SIMPLE_LABEL = f'''\
<?xml version="1.0" encoding="UTF-8"?>
<Product_Observational xmlns="{NS_PDS}" xmlns:xsi="{NS_XSI}"
 xsi:schemaLocation="{NS_PDS} https://pds.nasa.gov/pds4/pds/v1/PDS4_PDS_1L00.xsd">
    <Identification_Area>
        <logical_identifier>urn:nasa:pds:test_simple:index:row1</logical_identifier>
        <version_id>1.0</version_id>
        <title>Row 1</title>
    </Identification_Area>
</Product_Observational>
'''

LABEL_BOM = '﻿' + SIMPLE_LABEL  # serialised to bytes EF BB BF + ...

LABEL_NO_DEFAULT_NS = f'''\
<?xml version="1.0" encoding="UTF-8"?>
<pds:Product_Observational xmlns:pds="{NS_PDS}" xmlns:xsi="{NS_XSI}"
 xsi:schemaLocation="{NS_PDS} https://pds.nasa.gov/pds4/pds/v1/PDS4_PDS_1L00.xsd">
    <pds:Identification_Area>
        <pds:logical_identifier>urn:nasa:pds:t:t:t</pds:logical_identifier>
        <pds:version_id>1.0</pds:version_id>
    </pds:Identification_Area>
</pds:Product_Observational>
'''

LABEL_WITH_NIL = f'''\
<?xml version="1.0" encoding="UTF-8"?>
<Product_Observational xmlns="{NS_PDS}" xmlns:xsi="{NS_XSI}"
 xsi:schemaLocation="{NS_PDS} https://pds.nasa.gov/pds4/pds/v1/PDS4_PDS_1L00.xsd">
    <Identification_Area>
        <logical_identifier>urn:nasa:pds:test_simple:index:row1</logical_identifier>
        <version_id>1.0</version_id>
        <title>Row 1</title>
    </Identification_Area>
    <Time_Coordinates>
        <stop_date_time xsi:nil="true" nilReason="missing"/>
    </Time_Coordinates>
</Product_Observational>
'''

NILLABLE: Mapping[str, NillableEntry] = {
    'pds:ASCII_Date_YMD': NillableEntry(
        inapplicable='0001-01-01',
        missing='0002-01-01',
        unknown='0003-01-01',
        anticipated='0004-01-01',
    ),
}


class _StubResolver(SchemaTypeResolver):
    """Typed, network-free stand-in for the real XSD type resolver.

    Overrides :meth:`~pds4indextools.schema_types.SchemaTypeResolver.resolve`
    to return a fixed data type so the nil-substitution paths can be exercised
    without a seeded XSD cache. It deliberately does not call the base
    initializer; only ``resolve`` is invoked by the scraper.

    Parameters:
        data_type: The base type string every ``resolve`` call returns.
    """

    def __init__(self, data_type: str = 'pds:ASCII_Date_YMD') -> None:
        """Store the fixed data type this stub resolver returns.

        Parameters:
            data_type: The base type string every ``resolve`` call returns.
        """
        self._data_type = data_type

    def resolve(self, xpath_leaf_tag: str) -> str:
        """Return the fixed data type regardless of ``xpath_leaf_tag``.

        Parameters:
            xpath_leaf_tag: The canonical leaf tag being resolved (ignored).

        Returns:
            The fixed data type supplied at construction.
        """
        return self._data_type


def _label(
    id_area: str,
    body: str = '',
    *,
    xmlns_extra: str = '',
    schema_location: str = SCHEMA_LOC,
) -> str:
    """Build a minimal PDS4 label string around an Identification_Area.

    Parameters:
        id_area: The inner XML of the ``<Identification_Area>`` element.
        body: Extra XML appended after the Identification_Area.
        xmlns_extra: Extra attributes injected on the root element.
        schema_location: The value of the ``xsi:schemaLocation`` attribute.

    Returns:
        A complete label document string.
    """
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<Product_Observational xmlns="{NS_PDS}" xmlns:xsi="{NS_XSI}"{xmlns_extra}\n'
        f' xsi:schemaLocation="{schema_location}">\n'
        '    <Identification_Area>\n'
        f'{id_area}'
        '    </Identification_Area>\n'
        f'{body}'
        '</Product_Observational>\n'
    )


def _id(lid: str = DEFAULT_LID, version: str = '1.0') -> str:
    """Return a standard Identification_Area body with one LID and version.

    Parameters:
        lid: The logical-identifier text.
        version: The version-id text.

    Returns:
        The inner XML of an Identification_Area with the two required leaves.
    """
    return (
        f'        <logical_identifier>{lid}</logical_identifier>\n'
        f'        <version_id>{version}</version_id>\n'
    )


def _write(tmp_path: Path, name: str, content: str) -> Path:
    """Write ``content`` to ``tmp_path / name`` as UTF-8 and return the path."""
    path = tmp_path / name
    path.write_text(content, encoding='utf-8')
    return path


def _scrape(
    path: Path,
    *,
    bundle_root: Path | None = None,
    resolver: SchemaTypeResolver | None = None,
    nillable_config: Mapping[str, NillableEntry] | None = None,
    fixed_width_mode: bool = False,
    seen_lids: dict[str, Path] | None = None,
) -> ScrapeResult:
    """Invoke :func:`scrape_label` with test-friendly defaults."""
    return scrape_label(
        path,
        bundle_root=bundle_root if bundle_root is not None else path.parent,
        resolver=resolver if resolver is not None else _StubResolver(),
        nillable_config=nillable_config if nillable_config is not None else NILLABLE,
        fixed_width_mode=fixed_width_mode,
        seen_lids=seen_lids,
    )


def _leaf_names(result: ScrapeResult) -> list[str]:
    """Return the local names of every scraped row key, in row order."""
    return [key.split('/')[-1].split('<')[0].split(':')[-1] for key in result.rows]


# --- Parsing and tree walk (R-SCRAPE-*, R-PARSE-*) ---------------------------


def test_scrape_simple_label_returns_rows_dict(tmp_path: Path) -> None:
    """A simple label is scraped into a rows dict keyed by canonical XPath.

    Implements R-SCRAPE-010, R-SCRAPE-020.
    """
    path = _write(tmp_path, 'simple.lblx', SIMPLE_LABEL)
    result = _scrape(path)
    title_keys = [k for k in result.rows if k.endswith('pds:title<1>')]
    assert len(title_keys) == 1
    assert result.rows[title_keys[0]] == 'Row 1'


def test_scrape_is_suffix_agnostic_xml_and_lblx_identical(tmp_path: Path) -> None:
    """A ``.xml`` label scrapes identically to a ``.lblx`` label (owner #1)."""
    lblx = _write(tmp_path, 'a.lblx', SIMPLE_LABEL)
    xml = _write(tmp_path, 'a.xml', SIMPLE_LABEL)
    result_lblx = _scrape(lblx)
    result_xml = _scrape(xml)
    assert result_lblx.rows == result_xml.rows
    assert result_lblx.lid == result_xml.lid


def test_scrape_pre_order_traversal_visits_every_element(tmp_path: Path) -> None:
    """Every leaf XPath is scraped and no parent element is stored.

    Implements R-SCRAPE-010, R-SCRAPE-030.
    """
    body = (
        '    <Observation_Area>\n'
        '        <first>1</first>\n'
        '        <group>\n'
        '            <second>2</second>\n'
        '            <third>3</third>\n'
        '        </group>\n'
        '        <fourth>4</fourth>\n'
        '    </Observation_Area>\n'
    )
    path = _write(tmp_path, 'nested.lblx', _label(_id(), body))
    result = _scrape(path)
    names = _leaf_names(result)
    assert names == [
        'logical_identifier',
        'version_id',
        'first',
        'second',
        'third',
        'fourth',
    ]
    assert not any(key.endswith('pds:group<1>') for key in result.rows)
    assert not any(key.endswith('pds:Observation_Area<1>') for key in result.rows)


def test_scrape_result_rows_order_is_dom_pre_order(tmp_path: Path) -> None:
    """The rows dict preserves DOM pre-order insertion (section 7.1 contract)."""
    body = (
        '    <Observation_Area>\n'
        '        <alpha>a</alpha>\n'
        '        <beta>b</beta>\n'
        '        <gamma>g</gamma>\n'
        '    </Observation_Area>\n'
    )
    path = _write(tmp_path, 'order.lblx', _label(_id(), body))
    result = _scrape(path)
    assert _leaf_names(result) == [
        'logical_identifier',
        'version_id',
        'alpha',
        'beta',
        'gamma',
    ]


def test_scrape_ignores_xml_comments(tmp_path: Path) -> None:
    """XML comment nodes are skipped by the leaf walk (R-SCRAPE-010)."""
    body = (
        '    <Observation_Area>\n'
        '        <!-- a comment node -->\n'
        '        <note>hello</note>\n'
        '    </Observation_Area>\n'
    )
    path = _write(tmp_path, 'comment.lblx', _label(_id(), body))
    result = _scrape(path)
    note_key = next(k for k in result.rows if k.endswith('pds:note<1>'))
    assert result.rows[note_key] == 'hello'


def test_scrape_attribute_not_scraped(tmp_path: Path) -> None:
    """Element attributes such as ``unit`` never become row keys (R-SCRAPE-040)."""
    body = (
        '    <Observation_Area>\n        <distance unit="m">5</distance>\n    </Observation_Area>\n'
    )
    path = _write(tmp_path, 'attr.lblx', _label(_id(), body))
    result = _scrape(path)
    assert not any('unit' in key for key in result.rows)
    assert any(key.endswith('pds:distance<1>') for key in result.rows)


def test_scrape_whitespace_collapsed(tmp_path: Path) -> None:
    """Internal whitespace runs collapse to single spaces (R-VAL-010)."""
    body = (
        '    <Observation_Area>\n        <comment>  a\n\tb  c </comment>\n    </Observation_Area>\n'
    )
    path = _write(tmp_path, 'ws.lblx', _label(_id(), body))
    result = _scrape(path)
    comment_key = next(k for k in result.rows if k.endswith('pds:comment<1>'))
    assert result.rows[comment_key] == 'a b c'


def test_scrape_bom_rejected(tmp_path: Path) -> None:
    """A UTF-8 BOM at the start of a label is rejected (R-PARSE-001)."""
    path = _write(tmp_path, 'bom.lblx', LABEL_BOM)
    with pytest.raises(ParseError) as exc_info:
        _scrape(path)
    assert 'BOM' in str(exc_info.value)


def test_scrape_invalid_xml_raises_parseerror(tmp_path: Path) -> None:
    """Malformed XML is re-raised as ParseError chained to XMLSyntaxError.

    Implements R-PARSE-002.
    """
    path = _write(tmp_path, 'bad.lblx', _label(_id(), '    <broken>\n'))
    with pytest.raises(ParseError) as exc_info:
        _scrape(path)
    assert 'parse' in str(exc_info.value).lower()
    assert isinstance(exc_info.value.__cause__, etree.XMLSyntaxError)


def test_scrape_no_default_namespace_raises_parseerror(tmp_path: Path) -> None:
    """A root declaring no default namespace is rejected (R-XP-013, T-XP-022)."""
    path = _write(tmp_path, 'nons.lblx', LABEL_NO_DEFAULT_NS)
    with pytest.raises(ParseError) as exc_info:
        _scrape(path)
    assert 'default namespace' in str(exc_info.value)


# --- Value content checks (R-VAL-020/030/040) --------------------------------


def test_scrape_non_ascii_byte_raises_scrapedvalueerror(tmp_path: Path) -> None:
    """A non-ASCII value character is rejected and names its XPath.

    Implements R-VAL-030 (T-CSV-040).
    """
    body = '    <Observation_Area>\n        <comment>café</comment>\n    </Observation_Area>\n'
    path = _write(tmp_path, 'nonascii.lblx', _label(_id(), body))
    with pytest.raises(ScrapedValueError) as exc_info:
        _scrape(path)
    assert 'comment' in str(exc_info.value)


def test_scrape_non_ascii_above_u00ff_raises_scrapedvalueerror(tmp_path: Path) -> None:
    """A codepoint above U+00FF is rejected, proving the isascii() check.

    Implements R-VAL-030.
    """
    body = '    <Observation_Area>\n        <comment>10€</comment>\n    </Observation_Area>\n'
    path = _write(tmp_path, 'euro.lblx', _label(_id(), body))
    with pytest.raises(ScrapedValueError) as exc_info:
        _scrape(path)
    assert 'comment' in str(exc_info.value)


def test_scrape_control_char_raises_scrapedvalueerror(tmp_path: Path) -> None:
    """An ASCII control character (0x7F) is rejected (R-VAL-020, T-CSV-050).

    The 0x07 codepoint named in the plan cannot appear in well-formed XML, so
    the equivalent control-character check uses 0x7F (DEL), which is a legal
    XML character and is covered by R-VAL-020's ``0x00-0x1F or 0x7F`` range.
    """
    body_control = (
        '    <Observation_Area>\n'
        f'        <comment>a{chr(0x7F)}b</comment>\n'
        '    </Observation_Area>\n'
    )
    path = _write(tmp_path, 'control.lblx', _label(_id(), body_control))
    with pytest.raises(ScrapedValueError) as exc_info:
        _scrape(path)
    assert 'comment' in str(exc_info.value)


def test_scrape_tab_in_value_collapsed_not_error(tmp_path: Path) -> None:
    """A tab collapses under R-VAL-010 before the R-VAL-020 check (T-CSV-050)."""
    body = '    <Observation_Area>\n        <comment>a\tb</comment>\n    </Observation_Area>\n'
    path = _write(tmp_path, 'tab.lblx', _label(_id(), body))
    result = _scrape(path)
    comment_key = next(k for k in result.rows if k.endswith('pds:comment<1>'))
    assert result.rows[comment_key] == 'a b'


def test_scrape_quote_in_value_variable_width_raises(tmp_path: Path) -> None:
    """A double quote is rejected in variable-width mode (R-VAL-040)."""
    body = '    <Observation_Area>\n        <comment>a"b</comment>\n    </Observation_Area>\n'
    path = _write(tmp_path, 'quote.lblx', _label(_id(), body))
    with pytest.raises(ScrapedValueError) as exc_info:
        _scrape(path, fixed_width_mode=False)
    assert 'comment' in str(exc_info.value)


def test_scrape_quote_in_value_fixed_width_passes(tmp_path: Path) -> None:
    """A double quote is kept verbatim in fixed-width mode (R-VAL-040)."""
    body = '    <Observation_Area>\n        <comment>a"b</comment>\n    </Observation_Area>\n'
    path = _write(tmp_path, 'quotefw.lblx', _label(_id(), body))
    result = _scrape(path, fixed_width_mode=True)
    comment_key = next(k for k in result.rows if k.endswith('pds:comment<1>'))
    assert result.rows[comment_key] == 'a"b'


# --- LID and version_id validation (R-LID-001/010/020) -----------------------


def test_scrape_valid_lid_accepted(tmp_path: Path) -> None:
    """A well-formed LID is accepted and recorded (R-LID-001, T-LID-001)."""
    path = _write(tmp_path, 'validlid.lblx', _label(_id('urn:nasa:pds:bundle:collection:product')))
    result = _scrape(path)
    assert result.lid == 'urn:nasa:pds:bundle:collection:product'


def test_scrape_no_urn_prefix_lid_rejected(tmp_path: Path) -> None:
    """A LID without the ``urn:`` prefix is rejected (R-LID-001, T-LID-010)."""
    path = _write(tmp_path, 'nourn.lblx', _label(_id('nasa:pds:bundle')))
    with pytest.raises(LidError) as exc_info:
        _scrape(path)
    assert 'nasa:pds:bundle' in str(exc_info.value)


def test_scrape_uppercase_lid_prefix_rejected(tmp_path: Path) -> None:
    """An uppercase ``URN:`` prefix is rejected (R-LID-001, T-LID-011)."""
    path = _write(tmp_path, 'upper.lblx', _label(_id('URN:NASA:PDS:b')))
    with pytest.raises(LidError) as exc_info:
        _scrape(path)
    assert 'URN:NASA:PDS:b' in str(exc_info.value)


def test_scrape_lid_with_only_three_tokens_rejected(tmp_path: Path) -> None:
    """A three-token LID fails the regex before bundle_name extraction.

    Implements R-LID-001 (T-AUTO-050).
    """
    path = _write(tmp_path, 'threetok.lblx', _label(_id('urn:a:b')))
    with pytest.raises(LidError) as exc_info:
        _scrape(path)
    assert 'urn:a:b' in str(exc_info.value)


def test_scrape_lid_with_seven_tokens_accepted(tmp_path: Path) -> None:
    """A full seven-token LID is accepted (R-LID-001)."""
    lid = 'urn:nasa:pds:bundle:collection:product:extra'
    path = _write(tmp_path, 'seventok.lblx', _label(_id(lid)))
    result = _scrape(path)
    assert result.lid == lid


def test_scrape_missing_logical_identifier_raises_liderror(tmp_path: Path) -> None:
    """A label with no logical_identifier is rejected (R-LID-001, T-LID-020)."""
    id_area = '        <version_id>1.0</version_id>\n'
    path = _write(tmp_path, 'nolid.lblx', _label(id_area))
    with pytest.raises(LidError) as exc_info:
        _scrape(path)
    assert 'logical_identifier' in str(exc_info.value)


def test_scrape_duplicate_logical_identifier_raises_liderror(tmp_path: Path) -> None:
    """Two logical_identifier elements are rejected (R-LID-001)."""
    id_area = (
        f'        <logical_identifier>{DEFAULT_LID}</logical_identifier>\n'
        f'        <logical_identifier>{DEFAULT_LID}</logical_identifier>\n'
        '        <version_id>1.0</version_id>\n'
    )
    path = _write(tmp_path, 'duplid.lblx', _label(id_area))
    with pytest.raises(LidError) as exc_info:
        _scrape(path)
    assert 'logical_identifier' in str(exc_info.value)


def test_scrape_missing_version_id_raises_liderror(tmp_path: Path) -> None:
    """A label with no version_id is rejected (R-LID-010, T-LID-030)."""
    id_area = f'        <logical_identifier>{DEFAULT_LID}</logical_identifier>\n'
    path = _write(tmp_path, 'nover.lblx', _label(id_area))
    with pytest.raises(LidError) as exc_info:
        _scrape(path)
    assert 'version_id' in str(exc_info.value)


def test_scrape_duplicate_version_id_raises_liderror(tmp_path: Path) -> None:
    """Two version_id elements are rejected (R-LID-010)."""
    id_area = (
        f'        <logical_identifier>{DEFAULT_LID}</logical_identifier>\n'
        '        <version_id>1.0</version_id>\n'
        '        <version_id>2.0</version_id>\n'
    )
    path = _write(tmp_path, 'dupver.lblx', _label(id_area))
    with pytest.raises(LidError) as exc_info:
        _scrape(path)
    assert 'version_id' in str(exc_info.value)


def test_cross_label_lid_collision_raises(tmp_path: Path) -> None:
    """A shared LID across two labels is rejected naming both paths.

    Implements R-LID-020 (T-LID-050).
    """
    path_a = _write(tmp_path, 'a.lblx', SIMPLE_LABEL)
    path_b = _write(tmp_path, 'b.lblx', SIMPLE_LABEL)
    seen_lids: dict[str, Path] = {}
    _scrape(path_a, seen_lids=seen_lids)
    with pytest.raises(LidError) as exc_info:
        _scrape(path_b, seen_lids=seen_lids)
    assert 'a.lblx' in str(exc_info.value)
    assert 'b.lblx' in str(exc_info.value)


def test_scrape_with_no_seen_lids_dict_skips_cross_label_check(tmp_path: Path) -> None:
    """Passing ``seen_lids=None`` skips the cross-label uniqueness check."""
    path = _write(tmp_path, 'dup.lblx', SIMPLE_LABEL)
    _scrape(path, seen_lids=None)
    result = _scrape(path, seen_lids=None)
    assert result.lid == DEFAULT_LID


# --- Auto-columns (section 8.2, R-FS-010) ------------------------------------


@pytest.mark.parametrize(
    ('byte_length', 'passes'),
    [(1, True), (254, True), (255, True), (256, False), (257, False), (1024, False)],
)
def test_filespec_byte_length_parametrized(
    tmp_path: Path,
    byte_length: int,
    passes: bool,
) -> None:
    """A filespec over 255 bytes is a hard label error (R-FS-010, T-AUTO-030)."""
    rel = _rel_path_of_length(byte_length)
    label_path = tmp_path / rel
    label_path.parent.mkdir(parents=True, exist_ok=True)
    label_path.write_text(SIMPLE_LABEL, encoding='utf-8')
    if passes:
        result = _scrape(label_path, bundle_root=tmp_path)
        assert len(result.auto_columns['filespec'].encode('utf-8')) == byte_length
    else:
        with pytest.raises(LabelError) as exc_info:
            _scrape(label_path, bundle_root=tmp_path)
        assert 'filespec' in str(exc_info.value)
        assert '255' in str(exc_info.value)


def _rel_path_of_length(n: int) -> str:
    """Return a POSIX relative path of exactly ``n`` bytes using ``a`` and ``/``."""
    parts: list[str] = []
    remaining = n
    while remaining > 200:
        parts.append('a' * 200)
        remaining -= 201
    parts.append('a' * remaining)
    return '/'.join(parts)


def test_auto_columns_filespec_uses_forward_slashes(tmp_path: Path) -> None:
    """The filespec always uses forward slashes via as_posix() (T-AUTO-020)."""
    sub = tmp_path / 'sub_dir'
    sub.mkdir()
    label_path = _write(sub, 'row.lblx', SIMPLE_LABEL)
    result = _scrape(label_path, bundle_root=tmp_path)
    assert result.auto_columns['filespec'] == 'sub_dir/row.lblx'
    assert '\\' not in result.auto_columns['filespec']


def test_auto_columns_lid_strips_whitespace(tmp_path: Path) -> None:
    """Surrounding whitespace is stripped from the lid auto-column (T-AUTO-001)."""
    id_area = (
        f'        <logical_identifier>   {DEFAULT_LID}   </logical_identifier>\n'
        '        <version_id>1.0</version_id>\n'
    )
    path = _write(tmp_path, 'lidws.lblx', _label(id_area))
    result = _scrape(path)
    assert result.auto_columns['lid'] == DEFAULT_LID


def test_auto_columns_lidvid_concatenates_correctly(tmp_path: Path) -> None:
    """The lidvid auto-column is ``lid + '::' + version`` (T-AUTO-010)."""
    path = _write(tmp_path, 'lidvid.lblx', SIMPLE_LABEL)
    result = _scrape(path)
    assert result.auto_columns['lidvid'] == f'{DEFAULT_LID}::1.0'


def test_auto_columns_filename_is_basename(tmp_path: Path) -> None:
    """The filename auto-column is the label path basename (section 8.2)."""
    path = _write(tmp_path, 'basename.lblx', SIMPLE_LABEL)
    result = _scrape(path)
    assert result.auto_columns['filename'] == 'basename.lblx'


def test_auto_columns_bundle_name_extracts_4th_colon_token(tmp_path: Path) -> None:
    """The bundle_name auto-column is the 4th colon token of the lid (T-AUTO-040)."""
    path = _write(tmp_path, 'bundle.lblx', _label(_id('urn:nasa:pds:bundle_x:coll:prod')))
    result = _scrape(path)
    assert result.auto_columns['bundle_name'] == 'bundle_x'


# --- Nil and missing handling (R-NIL-*, R-MISS-*) ----------------------------


def _nil_label(nil_attrs: str) -> str:
    """Return a label whose stop_date_time carries ``nil_attrs``."""
    body = (
        f'    <Time_Coordinates>\n        <stop_date_time {nil_attrs}/>\n    </Time_Coordinates>\n'
    )
    return _label(_id(), body)


def test_nil_substitution_known_dtype(tmp_path: Path) -> None:
    """A nilled element of a known dtype substitutes the config value.

    Implements R-NIL-010, R-NIL-020 (T-NIL-001).
    """
    path = _write(tmp_path, 'nil.lblx', LABEL_WITH_NIL)
    result = _scrape(path, resolver=_StubResolver('pds:ASCII_Date_YMD'))
    nil_key = next(k for k in result.rows if k.endswith('pds:stop_date_time<1>'))
    assert result.rows[nil_key] == '0002-01-01'


def test_nil_substitution_bad_reason_raises_nilerror(tmp_path: Path) -> None:
    """An unrecognized nilReason is rejected naming the reason (R-NIL-010)."""
    path = _write(tmp_path, 'badreason.lblx', _nil_label('xsi:nil="true" nilReason="bogus"'))
    with pytest.raises(NilError) as exc_info:
        _scrape(path)
    assert 'bogus' in str(exc_info.value)


def test_nil_missing_nilreason_raises_nilerror(tmp_path: Path) -> None:
    """A nilled element with no nilReason is rejected (R-NIL-010)."""
    path = _write(tmp_path, 'noreason.lblx', _nil_label('xsi:nil="true"'))
    with pytest.raises(NilError) as exc_info:
        _scrape(path)
    assert 'nilReason' in str(exc_info.value)


def test_nil_unknown_dtype_in_config_raises_nilerror(tmp_path: Path) -> None:
    """A resolved dtype absent from the config is rejected (R-NIL-030, T-NIL-020)."""
    path = _write(tmp_path, 'unknowndtype.lblx', _nil_label('xsi:nil="true" nilReason="missing"'))
    with pytest.raises(NilError) as exc_info:
        _scrape(path, resolver=_StubResolver('pds:Unmapped_Type'))
    assert 'pds:Unmapped_Type' in str(exc_info.value)


def test_empty_text_no_nil_attribute_treated_as_absent(tmp_path: Path) -> None:
    """An empty leaf with no xsi:nil is omitted from rows (R-NIL-040, T-NIL-030)."""
    body = '    <Observation_Area>\n        <empty></empty>\n    </Observation_Area>\n'
    path = _write(tmp_path, 'empty.lblx', _label(_id(), body))
    result = _scrape(path)
    assert not any(key.endswith('pds:empty<1>') for key in result.rows)


# --- Renumbering, namespaces, schema URLs ------------------------------------


def test_renumber_applied_after_walk(tmp_path: Path) -> None:
    """Sibling blocks are renumbered to dense <1>,<2>,<3> after the walk (T-XP-020)."""
    body = ''.join(
        f'    <Observing_System>\n        <name>{value}</name>\n    </Observing_System>\n'
        for value in ('a', 'b', 'c')
    )
    path = _write(tmp_path, 'renumber.lblx', _label(_id(), body))
    result = _scrape(path)
    indexes = {
        key.split('pds:Observing_System<')[1][0]
        for key in result.rows
        if 'Observing_System<' in key
    }
    assert indexes == {'1', '2', '3'}


def test_namespaces_recorded(tmp_path: Path) -> None:
    """The namespaces map aliases the default to ``pds`` and preserves others.

    Implements section 10.
    """
    path = _write(tmp_path, 'ns.lblx', SIMPLE_LABEL)
    result = _scrape(path)
    assert result.namespaces['pds'] == NS_PDS
    assert result.namespaces['xsi'] == NS_XSI


def test_schema_urls_recorded_in_declared_order(tmp_path: Path) -> None:
    """The schema_urls tuple preserves the declared schemaLocation order."""
    pds_url = 'https://pds.nasa.gov/pds4/pds/v1/PDS4_PDS_1L00.xsd'
    geom_url = 'https://pds.nasa.gov/pds4/geom/v1/PDS4_GEOM_1L00_2000.xsd'
    loc = f'{NS_PDS} {pds_url} {NS_GEOM} {geom_url}'
    path = _write(tmp_path, 'schemaurls.lblx', _label(_id(), schema_location=loc))
    result = _scrape(path)
    assert result.schema_urls == (pds_url, geom_url)


def test_schema_urls_absent_when_no_schema_location(tmp_path: Path) -> None:
    """A label without xsi:schemaLocation records an empty schema_urls tuple."""
    label = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<Product_Observational xmlns="{NS_PDS}" xmlns:xsi="{NS_XSI}">\n'
        '    <Identification_Area>\n'
        f'{_id()}'
        '    </Identification_Area>\n'
        '</Product_Observational>\n'
    )
    path = _write(tmp_path, 'noschema.lblx', label)
    result = _scrape(path)
    assert result.schema_urls == ()


def test_childless_root_label_raises_liderror(tmp_path: Path) -> None:
    """A label whose root has no children is walked then rejected (R-LID-001)."""
    label = f'<?xml version="1.0" encoding="UTF-8"?>\n<Product_Observational xmlns="{NS_PDS}"/>\n'
    path = _write(tmp_path, 'childless.lblx', label)
    with pytest.raises(LidError) as exc_info:
        _scrape(path)
    assert 'logical_identifier' in str(exc_info.value)
