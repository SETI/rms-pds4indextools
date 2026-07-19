"""Label scraping and validation for pds4indextools.

This package turns one PDS4 label file into a validated
:class:`~pds4indextools.scraper.ScrapeResult` via
:func:`~pds4indextools.scraper.scrape_label`, implementing spec section 8
(R-LID-*, R-AUTO-*, R-FS-010), section 9 (R-PARSE-*, R-SCRAPE-*, R-VAL-*),
section 10 (R-XP-013, R-XP-020), and section 12 (R-NIL-*, R-MISS-*).

It is split into single-responsibility private submodules -- ``_parse``
(parsing, BOM, namespace, walk), ``_value`` (normalization and content
checks), ``_nil`` (nil substitution), ``_lid`` (identifier validation and
auto-columns), and ``_orchestrator`` (the top-level pipeline) -- and re-exports
only the two public names below. Consumers import from
``pds4indextools.scraper``; the private submodules are an implementation
detail.
"""

from pds4indextools.scraper._orchestrator import ScrapeResult, scrape_label

__all__ = [
    'ScrapeResult',
    'scrape_label',
]
