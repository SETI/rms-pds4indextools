# Test XSD seeds

Hand-curated PDS4 XSD snippets sufficient to exercise the query-chain
resolution in `pds4indextools.schema_types.SchemaTypeResolver`. These
intentionally do **not** mirror the real PDS4 schemas; they only
declare the simple types that the test fixtures reference. Every
golden output is generated against THESE seeds, never against the live
schemas.

`pds_v1_basic.xsd` serves both `PDS4_PDS_1L00.xsd` and
`PDS4_PDS_1K00.xsd` fixture URLs; `geom_v1.xsd` / `rings_v1.xsd` serve
the geom and rings URLs; `pds_v1_units.xsd` exercises the `_WO_Units`
fallback. The mapping from fixture URL to seed file is
`_FIXTURE_SCHEMA_URLS` in `tests/conftest.py` (mirrored by
`scripts/generate_expected_outputs.py`).

Only tests marked `@pytest.mark.live` download real schemas from
`https://pds.nasa.gov/` (R-SCH-010, R-TST-030 as amended).
