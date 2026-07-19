"""Unit tests for :mod:`pds4indextools.xpath_norm`.

These tests pin down XPath canonicalization and per-label renumbering of
spec section 10 (R-XP-001..R-XP-030): default-namespace aliasing to
``pds:`` (R-XP-010), verbatim preservation of non-default prefixes
(R-XP-011), the always-present ``<n>`` occurrence predicate (R-XP-002),
forward-slash joining with no leading slash (R-XP-003), the missing
default-namespace error (R-XP-013), dense renumbering of structural lxml
indexes (R-XP-020), the non-monotone interleave error (R-XP-021), and
first-occurrence order preservation (R-XP-030, R-XPL-010).

Per the plan's boundary rule (critique skill section 20) every test in this
file imports ONLY the public functions of
:mod:`pds4indextools.xpath_norm`; the private ``_XPathPart`` dataclass and
``_SEGMENT_RE`` regex are exercised exclusively through
:func:`~pds4indextools.xpath_norm.canonicalize_xpath` and
:func:`~pds4indextools.xpath_norm.renumber_xpaths`. The exception classes
are imported from :mod:`pds4indextools.errors`, which owns them.
"""

import pytest

from pds4indextools.errors import ParseError, XPathError
from pds4indextools.xpath_norm import canonicalize_xpath, renumber_xpaths

_PDS_NS = 'http://pds.nasa.gov/pds4/pds/v1'
_GEOM_NS = 'http://pds.nasa.gov/pds4/geom/v1'


def test_canonicalize_default_namespace_aliased_to_pds() -> None:
    """The default namespace (key ``None``) aliases to ``pds:`` (T-XP-001, R-XP-010)."""
    result = canonicalize_xpath(
        f'/{{{_PDS_NS}}}Product_Observational[1]',
        {None: _PDS_NS},
    )
    assert result == 'pds:Product_Observational<1>'


def test_canonicalize_non_default_namespace_prefix_preserved() -> None:
    """A non-default prefix is preserved verbatim (T-XP-002, R-XP-011)."""
    result = canonicalize_xpath(
        f'/{{{_PDS_NS}}}Product_Observational[1]/{{{_GEOM_NS}}}Foo[1]',
        {None: _PDS_NS, 'geom': _GEOM_NS},
    )
    assert result == 'pds:Product_Observational<1>/geom:Foo<1>'


def test_canonicalize_single_occurrence_emits_predicate_1() -> None:
    """An absent ``[n]`` predicate still produces ``<1>`` (T-XP-010, R-XP-002)."""
    result = canonicalize_xpath(f'/{{{_PDS_NS}}}Product_Observational', {None: _PDS_NS})
    assert result == 'pds:Product_Observational<1>'


def test_canonicalize_nested_path_multiple_segments() -> None:
    """A three-segment path canonicalizes every segment (R-XP-003)."""
    raw = (
        f'/{{{_PDS_NS}}}Product_Observational[1]'
        f'/{{{_PDS_NS}}}Observation_Area[2]'
        f'/{{{_PDS_NS}}}name[1]'
    )
    result = canonicalize_xpath(raw, {None: _PDS_NS})
    assert result == 'pds:Product_Observational<1>/pds:Observation_Area<2>/pds:name<1>'


def test_canonicalize_no_default_namespace_raises_parseerror() -> None:
    """A label with no default namespace raises ParseError (T-XP-022, R-XP-013)."""
    with pytest.raises(ParseError, match='no default namespace'):
        canonicalize_xpath(f'/{{{_GEOM_NS}}}Foo[1]', {'geom': _GEOM_NS})


def test_canonicalize_malformed_segment_raises_parseerror() -> None:
    """A segment lacking namespace braces raises ParseError (edge case)."""
    with pytest.raises(ParseError, match='malformed lxml xpath segment'):
        canonicalize_xpath('/foo[1]', {None: _PDS_NS})


def test_canonicalize_undeclared_namespace_raises_parseerror() -> None:
    """A segment whose namespace URI is absent from nsmap raises ParseError."""
    with pytest.raises(ParseError, match='is not declared on the label root'):
        canonicalize_xpath(
            f'/{{{_PDS_NS}}}A[1]/{{http://example.com/undeclared}}B[1]',
            {None: _PDS_NS},
        )


def test_canonicalize_segment_with_dot_in_localname() -> None:
    """A dotted local name canonicalizes intact (regex coverage)."""
    result = canonicalize_xpath(f'/{{{_PDS_NS}}}Foo.Bar[1]', {None: _PDS_NS})
    assert result == 'pds:Foo.Bar<1>'


def test_canonicalize_non_ascii_element_name_accepted() -> None:
    """A non-ASCII element name is accepted, not ASCII-restricted (owner decision #5)."""
    result = canonicalize_xpath(f'/{{{_PDS_NS}}}Résumé[1]', {None: _PDS_NS})
    assert result == 'pds:Résumé<1>'


def test_canonicalize_xpath_with_single_segment() -> None:
    """A root-only path canonicalizes to a single segment (edge case)."""
    result = canonicalize_xpath(f'/{{{_PDS_NS}}}Foo[1]', {None: _PDS_NS})
    assert result == 'pds:Foo<1>'


def test_renumber_three_siblings_2_5_7_to_1_2_3() -> None:
    """Structural indexes 2/5/7 renumber to a dense 1/2/3 (T-XP-020, R-XP-020)."""
    result = renumber_xpaths(['pds:A<2>', 'pds:A<5>', 'pds:A<7>'])
    assert result == {
        'pds:A<2>': 'pds:A<1>',
        'pds:A<5>': 'pds:A<2>',
        'pds:A<7>': 'pds:A<3>',
    }


def test_renumber_preserves_unique_indexes_when_already_monotone() -> None:
    """Distinct sibling tags each at ``<1>`` are left unchanged (R-XP-020)."""
    result = renumber_xpaths(['pds:A<1>', 'pds:B<1>', 'pds:C<1>'])
    assert result == {
        'pds:A<1>': 'pds:A<1>',
        'pds:B<1>': 'pds:B<1>',
        'pds:C<1>': 'pds:C<1>',
    }


def test_renumber_handles_multiple_parents_independently() -> None:
    """A repeated tag is renumbered separately under each distinct parent (R-XP-020)."""
    result = renumber_xpaths(
        [
            'pds:A<3>/pds:B<2>',
            'pds:A<3>/pds:B<5>',
            'pds:A<8>/pds:B<2>',
        ]
    )
    assert result == {
        'pds:A<3>/pds:B<2>': 'pds:A<1>/pds:B<1>',
        'pds:A<3>/pds:B<5>': 'pds:A<1>/pds:B<2>',
        'pds:A<8>/pds:B<2>': 'pds:A<2>/pds:B<1>',
    }


def test_renumber_non_monotone_interleave_raises_xpatherror() -> None:
    """A non-monotone interleave raises XPathError (T-XP-021, R-XP-021)."""
    with pytest.raises(XPathError, match='non-monotone interleave'):
        renumber_xpaths(['pds:A<2>/pds:B<1>', 'pds:A<1>/pds:B<1>'])


def test_renumber_non_monotone_error_cites_offending_and_prior_xpath() -> None:
    """The XPathError cites both the offending and prior conflicting XPath (R-XP-021)."""
    with pytest.raises(XPathError) as exc_info:
        renumber_xpaths(['pds:A<2>/pds:B<1>', 'pds:A<1>/pds:B<1>'])
    message = str(exc_info.value)
    assert 'pds:A<1>/pds:B<1>' in message


def test_renumber_non_monotone_error_names_prior_key() -> None:
    """The XPathError names the prior key that closed the bucket (R-XP-021)."""
    with pytest.raises(XPathError) as exc_info:
        renumber_xpaths(['pds:A<2>/pds:B<1>', 'pds:A<1>/pds:B<1>'])
    message = str(exc_info.value)
    assert 'conflicts with pds:A<2>/pds:B<1>' in message


def test_renumber_first_occurrence_order_preserved() -> None:
    """The output dict iterates in input (first-occurrence) order (T-XP-030, R-XP-030)."""
    inputs = ['pds:C<4>', 'pds:A<9>', 'pds:B<2>']
    result = renumber_xpaths(inputs)
    assert list(result.keys()) == inputs


@pytest.mark.parametrize(
    'inputs',
    [
        [],
        ['pds:A<1>'],
        ['pds:A<2>', 'pds:A<5>'],
        ['pds:A<1>', 'pds:A<2>', 'pds:A<3>'],
    ],
)
def test_renumber_input_output_invariants_parametrized(inputs: list[str]) -> None:
    """Renumbering preserves the key set and order and is idempotent (R-XP-020/030).

    Per the critique skill (sections 5 and 9): (a) the output keys equal the
    inputs as a set, (b) the output-key order matches the input order, and
    (c) feeding the renumbered values back through
    :func:`~pds4indextools.xpath_norm.renumber_xpaths` is the identity.
    """
    out = renumber_xpaths(inputs)
    assert set(out.keys()) == set(inputs)
    assert list(out.keys()) == list(inputs)
    renumbered_values = list(out.values())
    round_trip = renumber_xpaths(renumbered_values)
    assert round_trip == {value: value for value in renumbered_values}
