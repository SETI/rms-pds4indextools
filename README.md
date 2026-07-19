# rms-pds4indextools

<!-- pyml disable MD025 -->

[![GitHub release; latest by date](https://img.shields.io/github/v/release/SETI/rms-pds4indextools)](https://github.com/SETI/rms-pds4indextools/releases)
[![GitHub Release Date](https://img.shields.io/github/release-date/SETI/rms-pds4indextools)](https://github.com/SETI/rms-pds4indextools/releases)
[![Test Status](https://img.shields.io/github/actions/workflow/status/SETI/rms-pds4indextools/run-tests.yml?branch=main)](https://github.com/SETI/rms-pds4indextools/actions)
[![Documentation Status](https://readthedocs.org/projects/rms-pds4indextools/badge/?version=latest)](https://rms-pds4indextools.readthedocs.io/en/latest/?badge=latest)
[![Code coverage](https://img.shields.io/codecov/c/github/SETI/rms-pds4indextools/main?logo=codecov)](https://codecov.io/gh/SETI/rms-pds4indextools)
<br />
[![PyPI - Version](https://img.shields.io/pypi/v/rms-pds4indextools)](https://pypi.org/project/rms-pds4indextools)
[![PyPI - Format](https://img.shields.io/pypi/format/rms-pds4indextools)](https://pypi.org/project/rms-pds4indextools)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/rms-pds4indextools)](https://pypi.org/project/rms-pds4indextools)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/rms-pds4indextools)](https://pypi.org/project/rms-pds4indextools)
<br />
[![GitHub commits since latest release](https://img.shields.io/github/commits-since/SETI/rms-pds4indextools/latest)](https://github.com/SETI/rms-pds4indextools/commits/main/)
[![GitHub commit activity](https://img.shields.io/github/commit-activity/m/SETI/rms-pds4indextools)](https://github.com/SETI/rms-pds4indextools/commits/main/)
[![GitHub last commit](https://img.shields.io/github/last-commit/SETI/rms-pds4indextools)](https://github.com/SETI/rms-pds4indextools/commits/main/)
<br />
[![Number of GitHub open issues](https://img.shields.io/github/issues-raw/SETI/rms-pds4indextools)](https://github.com/SETI/rms-pds4indextools/issues)
[![Number of GitHub closed issues](https://img.shields.io/github/issues-closed-raw/SETI/rms-pds4indextools)](https://github.com/SETI/rms-pds4indextools/issues)
[![Number of GitHub open pull requests](https://img.shields.io/github/issues-pr-raw/SETI/rms-pds4indextools)](https://github.com/SETI/rms-pds4indextools/pulls)
[![Number of GitHub closed pull requests](https://img.shields.io/github/issues-pr-closed-raw/SETI/rms-pds4indextools)](https://github.com/SETI/rms-pds4indextools/pulls)
<br />
![GitHub License](https://img.shields.io/github/license/SETI/rms-pds4indextools)
[![Number of GitHub stars](https://img.shields.io/github/stars/SETI/rms-pds4indextools)](https://github.com/SETI/rms-pds4indextools/stargazers)
![GitHub forks](https://img.shields.io/github/forks/SETI/rms-pds4indextools)
[![DOI](https://zenodo.org/badge/rms-pds4indextools.svg)](https://zenodo.org/badge/latestdoi/rms-pds4indextools)
<!-- start-after-point -->

# Features

`rms-pds4indextools` scrapes PDS4 XML labels into a deterministic index CSV
and its paired PDS4 label. It exposes the `pds4_create_xml_index`
command-line program and a matching programmatic API.

- Generate an index CSV from a bundle of PDS4 labels.
- Generate the paired `.lblx` PDS4 label that describes the CSV.
- Configure the output columns with XPath selectors and auto tokens.
- Merge layered YAML configuration files onto a packaged default.
- Emit a starter columns block from a bundle with `generate_xpath_list`.

# Installation

The `pds4indextools` module is available via the `rms-pds4indextools` package on PyPI and can be
installed with:

```sh
pip install rms-pds4indextools
```

# Getting Started

Generate an index file from the single-label `simple_pds_only` example
bundle. Label discovery is glob-driven, so quote the pattern to keep the
shell from expanding it:

```sh
pds4_create_xml_index generate_index_file \
    --bundle-root tests/data/bundles/simple_pds_only \
    --config-file tests/data/configs/simple.yaml \
    --output-file index.csv \
    '**/*.lblx'
```

Usage examples:

The command writes `index.csv`:

```text
LID,FILE_NAME,TITLE
urn:nasa:pds:test_simple:index:row1,row1.lblx,Row 1
```

It also writes `index.lblx`, a PDS4 label that describes the CSV.

Details are available in the [module documentation](https://rms-pds4indextools.readthedocs.io/en/latest/module.html).

# Contributing

Information on contributing to this package can be found in the
[Contributing Guide](https://github.com/SETI/rms-pds4indextools/blob/main/CONTRIBUTING.md).

# Links

- [Documentation](https://rms-pds4indextools.readthedocs.io)
- [Repository](https://github.com/SETI/rms-pds4indextools)
- [Issue tracker](https://github.com/SETI/rms-pds4indextools/issues)
- [PyPi](https://pypi.org/project/rms-pds4indextools)

# Licensing

This code is licensed under the [Apache License v2.0](https://github.com/SETI/rms-pds4indextools/blob/main/LICENSE).
