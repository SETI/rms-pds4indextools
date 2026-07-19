"""Configuration loading, deep-merging, and validation for pds4indextools.

This module owns the pydantic v2 schema for the tool's YAML configuration
(spec section 15) and the column-selection schema that replaced the former
mapping-file format (spec section 7). :func:`load_config` is the single
entry point: it reads the packaged default at
``templates/default_config.yaml`` (R-CFG-201), deep-merges each user config
on top in order (R-CFG-050/051), and validates the merged mapping into an
:class:`~pds4indextools.config.IndexConfig`. Any YAML parse error or
pydantic ``ValidationError`` is wrapped in a
:exc:`~pds4indextools.errors.ConfigError` via ``raise ... from`` so the
original cause is preserved.

The models pin down: top-level ``extra='forbid'`` (R-CFG-020); the
``output`` and ``nillable`` entry shapes (R-CFG-021/023); the pass-through
``label_contents`` block with reserved-name rejection (R-CFG-022, R-LBL-012)
and the ``product_class`` literal (R-LBL-010); absolute-path enforcement for
``xsd_cache_dir`` (R-CFG-024/040); the ``columns`` list of
:class:`~pds4indextools.config.ColumnSpec` entries with exactly-one-selector,
auto-token, whitespace, charset, duplicate, and order rules (R-MAP-030/031,
R-MAP-040/043, R-MAP-300/312/320, R-AUTO-001); and sort-key shape parsing
(R-SORT-010/020).
"""

import importlib.resources
import os
from collections.abc import Sequence
from pathlib import Path
from typing import Annotated, Any, Literal, cast

import yaml
from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    model_validator,
)

from pds4indextools.errors import ConfigError

__all__ = [
    'AUTO_COLUMN_TOKENS',
    'AbsolutePath',
    'CitationInformation',
    'ColumnSpec',
    'IndexConfig',
    'LabelContents',
    'ModificationDetail',
    'NillableEntry',
    'OutputSection',
    'load_config',
    'parse_sort_key',
]

# The five recognized auto-column tokens (R-AUTO-001). Any other value in a
# column entry's ``auto`` field is a hard error.
AUTO_COLUMN_TOKENS: frozenset[str] = frozenset(
    {
        'lid',
        'lidvid',
        'filespec',
        'filename',
        'bundle_name',
    }
)

# Rendered once for diagnostics so an unknown-token error lists every valid
# token in a stable order (covers the old R-MAP-013 typo diagnostics).
_AUTO_COLUMN_TOKENS_DISPLAY = ', '.join(sorted(AUTO_COLUMN_TOKENS))

# BASE variables the tool computes itself; a user config must not shadow them
# (R-LBL-012). These are the section 14.2 rows marked "Override = no".
_RESERVED_LABEL_CONTENT_KEYS: frozenset[str] = frozenset(
    {
        'index_file_name',
        'Field_Content',
        'fields',
        'records',
        'Table_Character',
        'Table_Delimited',
        'Product_Ancillary',
        'Product_Metadata_Supplemental',
        'object_length_h',
        'object_length_t',
        'maximum_record_length',
    }
)


def _require_absolute(path: Path) -> Path:
    """Return ``path`` unchanged if it is absolute, else raise ``ValueError``.

    Parameters:
        path: The filesystem path to check.

    Returns:
        The same :class:`~pathlib.Path` when it is absolute.

    Raises:
        ValueError: If ``path`` is not absolute; the message includes the
            offending path text so pydantic surfaces it (R-CFG-040).
    """
    if not path.is_absolute():
        raise ValueError(f'path must be absolute: {path}')
    return path


AbsolutePath = Annotated[Path, AfterValidator(_require_absolute)]


def parse_sort_key(spec: str) -> tuple[str, bool]:
    """Parse a ``sort_by`` entry into its column name and sort direction.

    The accepted shapes are ``"col"`` (ascending), ``"+col"`` (ascending),
    and ``"-col"`` (descending). The leading sign is optional; the remaining
    text is the column name and is not validated for existence here
    (R-SORT-020 defers column-existence to sorting).

    Parameters:
        spec: The raw sort-key string.

    Returns:
        A ``(column_name, descending)`` tuple where ``descending`` is
        ``True`` only for a ``-`` prefix.

    Raises:
        ValueError: If ``spec`` is empty or has a malformed sign prefix.
    """
    if spec == '':
        raise ValueError('invalid sort key: empty string')
    if spec[0] == '+':
        column, descending = spec[1:], False
    elif spec[0] == '-':
        column, descending = spec[1:], True
    else:
        column, descending = spec, False
    if column == '' or column[0] in '+-':
        raise ValueError(f'invalid sort key: {spec!r}')
    return column, descending


def _validate_name_charset(name: str) -> None:
    """Enforce the R-MAP-043 charset on a non-blank column ``name``.

    Parameters:
        name: The raw (unstripped) column name to validate.

    Raises:
        ValueError: If ``name`` contains any character outside printable
            ASCII (0x20-0x7E), a comma, or a double-quote.
    """
    for character in name:
        if ord(character) < 0x20 or ord(character) > 0x7E:
            raise ValueError(
                f'column name contains a non-printable or non-ASCII character: {name!r}'
            )
    if ',' in name:
        raise ValueError(f'column name must not contain a comma: {name!r}')
    if '"' in name:
        raise ValueError(f'column name must not contain a double-quote: {name!r}')


def _reserved_label_content_keys() -> frozenset[str]:
    """Return the reserved BASE variable names forbidden in ``label_contents``.

    Returns:
        The frozen set of eleven reserved names from R-LBL-012.
    """
    return _RESERVED_LABEL_CONTENT_KEYS


class NillableEntry(BaseModel):
    """The four nilReason replacement values for one PDS4 data type.

    Each field is the literal written into the index CSV when a scraped value
    carries the corresponding ``nilReason`` attribute. The data-type name is
    the dict key in :attr:`IndexConfig.nillable`; this model holds only the
    four values and forbids any other key (R-CFG-023).

    Parameters:
        inapplicable: Replacement for ``nilReason="inapplicable"``.
        missing: Replacement for ``nilReason="missing"``.
        unknown: Replacement for ``nilReason="unknown"``.
        anticipated: Replacement for ``nilReason="anticipated"``.

    Implements R-CFG-023 and spec section 15.6.
    """

    model_config = ConfigDict(extra='forbid')

    inapplicable: str | int | float
    missing: str | int | float
    unknown: str | int | float
    anticipated: str | int | float


class OutputSection(BaseModel):
    """Output-format settings for the generated index CSV.

    Parameters:
        fixed_width: ``True`` selects a fixed-width character table;
            ``False`` (default) selects a comma-delimited table.
        sort_by: Ordered list of sort keys; each is parsed by
            :func:`parse_sort_key`. An empty list performs no re-sort
            (R-SORT-010).
        line_ending: Record terminator, either ``'LF'`` or ``'CRLF'``.

    Implements R-CFG-021 and R-SORT-010/020.
    """

    model_config = ConfigDict(extra='forbid')

    fixed_width: bool = False
    sort_by: list[str] = Field(default_factory=list)
    line_ending: Literal['LF', 'CRLF'] = 'LF'

    @model_validator(mode='after')
    def _validate_sort_by(self) -> 'OutputSection':
        """Validate that every sort key has a well-formed shape (R-SORT-020)."""
        for spec in self.sort_by:
            parse_sort_key(spec)
        return self


class CitationInformation(BaseModel):
    """Optional citation metadata passed through to the label template.

    Every field is optional; unknown keys are accepted (``extra='allow'``)
    and passed through to PdsTemplate as substitution variables.

    Parameters:
        author_list: One author string or a list of authors.
        editor_list: One editor string.
        publication_year: Publication year as an integer or string.
        doi: Digital object identifier.
        keyword: One keyword string or a list of keywords.
        description: Free-text description.
        Funding_Acknowledgement: Optional funding-acknowledgement mapping.

    Implements R-CFG-022.
    """

    model_config = ConfigDict(extra='allow')

    author_list: str | list[str] | None = None
    editor_list: str | None = None
    publication_year: int | str | None = None
    doi: str | None = None
    keyword: str | list[str] | None = None
    description: str | None = None
    Funding_Acknowledgement: dict[str, Any] | None = None


class ModificationDetail(BaseModel):
    """A single modification-history entry for the generated label.

    Parameters:
        modification_date: The modification date string.
        version_id: The version identifier string.
        description: A description of the modification.

    Unknown keys are accepted and passed through (``extra='allow'``).
    Normalization (wrapping a single entry, or generating a default when
    none is supplied) happens later in the label writer, not here (R-LBL-091).

    Implements R-CFG-022 and R-LBL-090.
    """

    model_config = ConfigDict(extra='allow')

    modification_date: str
    version_id: str
    description: str


class LabelContents(BaseModel):
    """Substitution variables for the generated index label.

    The two required fields are the LID and product class of the GENERATED
    index product. All other fields are optional, and unknown keys are
    accepted (``extra='allow'``) and passed through to PdsTemplate, EXCEPT
    the reserved BASE variable names the tool computes itself, which are
    rejected (R-LBL-012).

    Parameters:
        logical_identifier: The LID of the generated index product
            (required, R-CFG-030).
        product_class: Either ``'Product_Ancillary'`` or
            ``'Product_Metadata_Supplemental'`` (required, R-CFG-031,
            R-LBL-010).
        version_id: Optional version identifier of the generated product.
        title: Optional product title.
        Citation_Information: Optional citation metadata.
        Modification_Detail: Optional modification history, as a single
            entry, a list of entries, or ``None``.
        Internal_Reference: Optional list of internal-reference mappings.
        External_Reference: Optional list of external-reference mappings.
        Source_Product_Internal: Optional list of source-product mappings.
        Source_Product_External: Optional list of source-product mappings.
        File_Area_Ancillary: Optional file-area mapping.
        File_Area_Metadata: Optional file-area mapping.

    Implements R-CFG-022, R-CFG-030, R-CFG-031, R-LBL-010, and R-LBL-012.
    """

    model_config = ConfigDict(extra='allow')

    logical_identifier: str
    product_class: Literal['Product_Ancillary', 'Product_Metadata_Supplemental']
    version_id: str | None = None
    title: str | None = None
    Citation_Information: CitationInformation | None = None
    Modification_Detail: list[ModificationDetail] | ModificationDetail | None = None
    Internal_Reference: list[dict[str, Any]] | None = None
    External_Reference: list[dict[str, Any]] | None = None
    Source_Product_Internal: list[dict[str, Any]] | None = None
    Source_Product_External: list[dict[str, Any]] | None = None
    File_Area_Ancillary: dict[str, Any] | None = None
    File_Area_Metadata: dict[str, Any] | None = None

    @model_validator(mode='after')
    def _reject_reserved_keys(self) -> 'LabelContents':
        """Reject any pass-through key that shadows a reserved BASE variable."""
        extra_keys = self.__pydantic_extra__ or {}
        for key in extra_keys:
            if key in _reserved_label_content_keys():
                raise ValueError(
                    f'reserved BASE variable name {key!r} must not appear in label_contents'
                )
        return self


class ColumnSpec(BaseModel):
    """One output-column selector in the merged config's ``columns`` list.

    Exactly one of ``xpath`` or ``auto`` is set per entry. The emitted header
    is the stripped ``name`` when non-blank, else the raw selector text.

    Parameters:
        xpath: A canonical XPath selector matched by exact string equality;
            it must contain no internal whitespace.
        auto: One of the five auto-column tokens (:data:`AUTO_COLUMN_TOKENS`).
        name: The emitted CSV header; ``None`` or blank falls back to the
            selector text (R-MAP-012.1).

    Implements R-MAP-300, R-MAP-040, R-MAP-043, and R-AUTO-001.
    """

    model_config = ConfigDict(extra='forbid')

    xpath: str | None = None
    auto: str | None = None
    name: str | None = None

    @property
    def selector(self) -> str:
        """Return the raw selector text (the ``xpath`` or the ``auto`` token).

        Returns:
            The selector string; exactly one of ``xpath``/``auto`` is set
            after validation, so this never returns ``None``.
        """
        selector = self.xpath if self.xpath is not None else self.auto
        return cast('str', selector)

    @property
    def header(self) -> str:
        """Return the emitted CSV header for this column.

        Returns:
            The stripped ``name`` when it is non-blank, otherwise the raw
            selector text (R-MAP-012.1).
        """
        if self.name is not None and self.name.strip() != '':
            return self.name.strip()
        return self.selector

    @model_validator(mode='after')
    def _validate_entry(self) -> 'ColumnSpec':
        """Enforce the per-entry selector, token, whitespace, and name rules."""
        has_xpath = self.xpath is not None
        has_auto = self.auto is not None
        if has_xpath == has_auto:
            raise ValueError("exactly one of 'xpath' or 'auto' must be set per column entry")
        if has_auto and self.auto not in AUTO_COLUMN_TOKENS:
            raise ValueError(
                f'unknown auto-column token {self.auto!r}; '
                f'valid tokens are: {_AUTO_COLUMN_TOKENS_DISPLAY}'
            )
        if has_xpath and any(char.isspace() for char in cast('str', self.xpath)):
            raise ValueError(f'xpath selector must not contain whitespace: {self.xpath!r}')
        if self.name is not None and self.name.strip() != '':
            _validate_name_charset(self.name)
        return self


class IndexConfig(BaseModel):
    """The fully merged and validated tool configuration.

    Parameters:
        nillable: Per-data-type nilReason replacement values, keyed by PDS4
            data-type name.
        label_contents: Substitution variables for the generated label
            (required).
        output: Output-format settings.
        columns: Ordered output-column selectors, or ``None`` when no
            columns are configured. An explicitly empty list is rejected
            (R-MAP-312); the required-for-index-generation check lives in the
            CLI layer.
        xsd_cache_dir: Optional absolute directory for cached XSDs; a
            relative value is rejected (R-CFG-024/040).

    Implements R-CFG-020, R-CFG-052, R-MAP-030/031/312/320.
    """

    model_config = ConfigDict(extra='forbid')

    nillable: dict[str, NillableEntry] = Field(default_factory=dict)
    label_contents: LabelContents
    output: OutputSection = Field(default_factory=OutputSection)
    columns: list[ColumnSpec] | None = None
    xsd_cache_dir: AbsolutePath | None = None

    @model_validator(mode='after')
    def _validate_columns(self) -> 'IndexConfig':
        """Reject an empty columns list and any duplicate selector or header."""
        if self.columns is None:
            return self
        if len(self.columns) == 0:
            raise ValueError('columns list must not be empty')
        seen_selectors: dict[tuple[str, str], int] = {}
        for index, entry in enumerate(self.columns):
            key = (
                ('xpath', entry.xpath)
                if entry.xpath is not None
                else ('auto', cast('str', entry.auto))
            )
            if key in seen_selectors:
                raise ValueError(
                    f'duplicate column selector {key[1]!r} in entries '
                    f'{seen_selectors[key]} and {index}'
                )
            seen_selectors[key] = index
        seen_headers: dict[str, int] = {}
        for index, entry in enumerate(self.columns):
            header = entry.header
            if header in seen_headers:
                raise ValueError(
                    f'duplicate column header {header!r} in entries '
                    f'{seen_headers[header]} and {index}'
                )
            seen_headers[header] = index
        return self


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Return ``base`` deep-merged with ``overlay`` (R-CFG-050).

    Nested dicts are merged recursively; lists and scalars in ``overlay``
    replace those in ``base`` wholesale. Neither input is mutated.

    Parameters:
        base: The lower-priority mapping.
        overlay: The higher-priority mapping whose values win.

    Returns:
        A new merged mapping.
    """
    result = dict(base)
    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _load_default_config() -> dict[str, Any]:
    """Load the packaged default configuration mapping (R-CFG-201).

    Returns:
        The parsed ``templates/default_config.yaml`` mapping.
    """
    resource = importlib.resources.files('pds4indextools.templates').joinpath('default_config.yaml')
    text = resource.read_text(encoding='utf-8')
    return cast('dict[str, Any]', yaml.safe_load(text))


def _format_validation_error(error: ValidationError) -> str:
    """Render a pydantic ``ValidationError`` as a compact one-line message.

    Parameters:
        error: The pydantic validation error to render.

    Returns:
        A ``"loc: msg"`` summary for each sub-error, joined by ``"; "``, so
        offending field names and column indexes appear in the message.
    """
    parts: list[str] = []
    for detail in error.errors():
        location = '.'.join(str(item) for item in detail['loc'])
        message = detail['msg']
        parts.append(f'{location}: {message}' if location != '' else message)
    return '; '.join(parts)


def load_config(paths: Sequence[Path]) -> IndexConfig:
    """Load, deep-merge, and validate the configuration chain.

    The packaged default is loaded first; each path in ``paths`` is then
    read and deep-merged on top in order (R-CFG-050/051). The merged mapping
    is validated into an :class:`IndexConfig` (R-CFG-052). Each path is
    checked for existence, regular-file status, and readability at the
    function boundary before it is opened.

    Parameters:
        paths: The user config paths, already resolved to absolute paths by
            the caller (R-FS-001), in increasing priority order.

    Returns:
        The validated :class:`IndexConfig`.

    Raises:
        ConfigError: If a path is missing, not a regular file, unreadable,
            not a YAML mapping at the top level, fails to parse, or fails
            pydantic validation. Parse and validation failures chain the
            underlying cause via ``raise ... from`` (R-CFG-010/011,
            R-CFG-020..R-CFG-052).
    """
    merged = _load_default_config()
    for path in paths:
        if not path.exists():
            raise ConfigError(f'config file does not exist: {path}', file_path=path) from None
        if not path.is_file():
            raise ConfigError(
                f'config file is not a regular file: {path}', file_path=path
            ) from None
        if not os.access(path, os.R_OK):
            raise ConfigError(f'config file is not readable: {path}', file_path=path) from None
        text = path.read_text(encoding='utf-8')
        try:
            loaded = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise ConfigError(f'failed to parse YAML config file: {path}', file_path=path) from exc
        if not isinstance(loaded, dict):
            raise ConfigError(
                f'config file top level must be a mapping: {path}', file_path=path
            ) from None
        merged = _deep_merge(merged, loaded)
    # Ensure label_contents is at least an empty mapping so that a wholly
    # missing block yields the R-CFG-030/031 sub-field errors (naming both
    # logical_identifier and product_class) instead of a single opaque
    # "label_contents required" error.
    merged.setdefault('label_contents', {})
    try:
        return IndexConfig.model_validate(merged)
    except ValidationError as exc:
        file_path = paths[0] if len(paths) == 1 else None
        raise ConfigError(_format_validation_error(exc), file_path=file_path) from exc
