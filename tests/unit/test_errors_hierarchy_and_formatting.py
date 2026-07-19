"""Unit tests for the :mod:`pds4indextools.errors` exception hierarchy.

These tests pin down the exception tree of spec section 17.1, the shared
constructor/formatting contract of ``Pds4IndexError``, the
``FailSlowAggregateError`` aggregation behavior, the fail-slow eligibility
flags (R-ERR-001), and the exit-code constants (section 17.2). They cover
R-TST-050 (one condition per assert) and R-TST-051 (assert on message
content) for the error module.
"""

from pathlib import Path

import pytest

from pds4indextools import errors
from pds4indextools.errors import (
    EXIT_INTERNAL_ERROR,
    EXIT_RUNTIME_ERROR,
    EXIT_SIGINT,
    EXIT_USER_ERROR,
    CliError,
    ConfigError,
    FailSlowAggregateError,
    LabelError,
    LidError,
    NilError,
    OutputError,
    ParseError,
    Pds4IndexError,
    SchemaCacheError,
    SchemaError,
    SchemaNetworkError,
    SchemaResolutionError,
    SchemaVersionError,
    ScrapedValueError,
    XPathError,
)

ALL_SUBCLASSES: list[type[Pds4IndexError]] = [
    CliError,
    ConfigError,
    LabelError,
    ParseError,
    LidError,
    XPathError,
    NilError,
    ScrapedValueError,
    SchemaError,
    SchemaResolutionError,
    SchemaVersionError,
    SchemaNetworkError,
    SchemaCacheError,
    OutputError,
    FailSlowAggregateError,
]

LABEL_ERROR_SUBCLASSES: list[type[LabelError]] = [
    ParseError,
    LidError,
    XPathError,
    NilError,
    ScrapedValueError,
]

SCHEMA_ERROR_SUBCLASSES: list[type[SchemaError]] = [
    SchemaResolutionError,
    SchemaVersionError,
    SchemaNetworkError,
    SchemaCacheError,
]

EXPECTED_PUBLIC_SURFACE: set[str] = {
    'Pds4IndexError',
    'CliError',
    'ConfigError',
    'LabelError',
    'ParseError',
    'LidError',
    'XPathError',
    'NilError',
    'ScrapedValueError',
    'SchemaError',
    'SchemaResolutionError',
    'SchemaVersionError',
    'SchemaNetworkError',
    'SchemaCacheError',
    'OutputError',
    'FailSlowAggregateError',
    'EXIT_USER_ERROR',
    'EXIT_RUNTIME_ERROR',
    'EXIT_INTERNAL_ERROR',
    'EXIT_SIGINT',
}


def test_pds4indexerror_is_exception_subclass() -> None:
    """``Pds4IndexError`` is a subclass of the built-in ``Exception``."""
    assert issubclass(Pds4IndexError, Exception)


def test_pds4indexerror_constructor_stores_message_attribute() -> None:
    """The constructor stores its positional message on ``.message``."""
    err = Pds4IndexError('msg')
    assert err.message == 'msg'


def test_pds4indexerror_default_file_path_is_none() -> None:
    """``.file_path`` defaults to ``None`` when not supplied."""
    err = Pds4IndexError('msg')
    assert err.file_path is None


def test_pds4indexerror_default_lineno_is_none() -> None:
    """``.lineno`` defaults to ``None`` when not supplied."""
    err = Pds4IndexError('msg')
    assert err.lineno is None


def test_pds4indexerror_str_with_path_and_lineno() -> None:
    """``__str__`` renders ``path:lineno: message`` when both are set."""
    err = Pds4IndexError('msg', file_path=Path('foo.lblx'), lineno=42)
    assert str(err) == 'foo.lblx:42: msg'


def test_pds4indexerror_str_with_path_only() -> None:
    """``__str__`` renders ``path: message`` when only the path is set."""
    err = Pds4IndexError('msg', file_path=Path('foo.lblx'))
    assert str(err) == 'foo.lblx: msg'


def test_pds4indexerror_str_no_path() -> None:
    """``__str__`` renders the bare message when no context is set."""
    err = Pds4IndexError('msg')
    assert str(err) == 'msg'


def test_pds4indexerror_file_path_kept_as_path_object() -> None:
    """``.file_path`` retains the ``Path`` object, never a ``str``."""
    err = Pds4IndexError('msg', file_path=Path('foo.lblx'))
    assert isinstance(err.file_path, Path)


@pytest.mark.parametrize('subclass', ALL_SUBCLASSES)
def test_all_subclasses_inherit_from_pds4indexerror(
    subclass: type[Pds4IndexError],
) -> None:
    """Every declared subclass inherits from ``Pds4IndexError``."""
    assert issubclass(subclass, Pds4IndexError)


@pytest.mark.parametrize('subclass', LABEL_ERROR_SUBCLASSES)
def test_subclass_hierarchy_label_error_subclasses(
    subclass: type[LabelError],
) -> None:
    """The label-content errors all descend from ``LabelError``."""
    assert issubclass(subclass, LabelError)


@pytest.mark.parametrize('subclass', SCHEMA_ERROR_SUBCLASSES)
def test_subclass_hierarchy_schema_error_subclasses(
    subclass: type[SchemaError],
) -> None:
    """The XSD-related errors all descend from ``SchemaError``."""
    assert issubclass(subclass, SchemaError)


@pytest.mark.parametrize(
    'subclass',
    [LabelError, ParseError, LidError, XPathError, NilError, ScrapedValueError],
)
def test_fail_slow_eligible_flag_label_errors_true(
    subclass: type[LabelError],
) -> None:
    """Every ``LabelError``-tree class is fail-slow eligible (R-ERR-001)."""
    assert subclass.FAIL_SLOW_ELIGIBLE is True


@pytest.mark.parametrize(
    ('subclass', 'expected'),
    [
        (SchemaError, True),
        (SchemaResolutionError, True),
        (SchemaVersionError, True),
        (SchemaNetworkError, False),
        (SchemaCacheError, False),
    ],
)
def test_fail_slow_eligible_flag_schema_subclasses(
    subclass: type[SchemaError],
    expected: bool,
) -> None:
    """Schema content errors are fail-slow eligible; environment ones are not."""
    assert subclass.FAIL_SLOW_ELIGIBLE is expected


@pytest.mark.parametrize(
    'subclass',
    [Pds4IndexError, CliError, ConfigError, OutputError, FailSlowAggregateError],
)
def test_fail_slow_eligible_flag_user_errors_false(
    subclass: type[Pds4IndexError],
) -> None:
    """User-input and infrastructure errors are not fail-slow eligible."""
    assert subclass.FAIL_SLOW_ELIGIBLE is False


def test_failslowaggregateerror_stores_errors_list() -> None:
    """The aggregate stores the supplied sub-errors as a list."""
    sub_errors = [LidError('a'), ParseError('b')]
    err = FailSlowAggregateError(sub_errors)
    assert err.errors == sub_errors


def test_failslowaggregateerror_empty_list_raises_valueerror() -> None:
    """Constructing with an empty list raises ``ValueError``."""
    with pytest.raises(ValueError, match='at least one'):
        FailSlowAggregateError([])


def test_failslowaggregateerror_errors_is_defensive_copy() -> None:
    """Mutating the input list does not mutate the stored ``.errors``."""
    sub_errors = [LidError('a'), ParseError('b')]
    err = FailSlowAggregateError(sub_errors)
    sub_errors.append(NilError('c'))
    assert len(err.errors) == 2


def test_failslowaggregateerror_str_starts_with_count_prefix() -> None:
    """``__str__`` opens with the ``"<n> errors"`` count prefix."""
    err = FailSlowAggregateError([LidError('a'), ParseError('b')])
    assert str(err).startswith('2 errors')


def test_failslowaggregateerror_str_contains_first_sub_message() -> None:
    """``__str__`` includes the first sub-error's formatted form."""
    first = LidError('first-msg', file_path=Path('a.lblx'), lineno=1)
    err = FailSlowAggregateError([first, ParseError('second-msg')])
    assert str(first) in str(err)


def test_failslowaggregateerror_str_contains_second_sub_message() -> None:
    """``__str__`` includes the second sub-error's formatted form."""
    second = ParseError('second-msg', file_path=Path('b.lblx'), lineno=2)
    err = FailSlowAggregateError([LidError('first-msg'), second])
    assert str(second) in str(err)


def test_failslowaggregateerror_str_separates_messages_with_newline() -> None:
    """``__str__`` joins the sub-error messages with a newline."""
    err = FailSlowAggregateError([LidError('a'), ParseError('b')])
    assert '\n' in str(err)


@pytest.mark.parametrize(
    ('constant', 'expected'),
    [
        (EXIT_USER_ERROR, 1),
        (EXIT_RUNTIME_ERROR, 2),
        (EXIT_INTERNAL_ERROR, 3),
        (EXIT_SIGINT, 130),
    ],
)
def test_exit_code_constants(constant: int, expected: int) -> None:
    """The exit-code constants carry their spec section 17.2 values."""
    assert constant == expected


def test_all_exports_match_module_public_surface() -> None:
    """``__all__`` enumerates exactly the intended public names."""
    assert set(errors.__all__) == EXPECTED_PUBLIC_SURFACE


def test_raise_from_chains_traceback() -> None:
    """``raise ... from`` preserves the originating cause on ``__cause__``."""
    with pytest.raises(ParseError, match='x') as exc_info:
        raise ParseError('x') from ValueError('y')
    assert str(exc_info.value.__cause__).startswith('y')


def test_pds4indexerror_message_attribute_preserves_raw_text() -> None:
    """``.message`` keeps the raw text even when path/lineno are set."""
    err = Pds4IndexError('raw', file_path=Path('x'), lineno=3)
    assert err.message == 'raw'


def test_subclass_str_format_inherited() -> None:
    """A subclass reuses the base ``__str__`` context formatting."""
    err = LidError('msg', file_path=Path('a'), lineno=7)
    assert str(err) == 'a:7: msg'
