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

# Introduction

`pds4indextools` is a set of programs and modules for parsing PDS4 XML labels.
They were created and are maintained by the [Ring-Moon Systems Node](https://pds-rings.seti.org)
of NASA's [Planetary Data System (PDS)](https://pds.nasa.gov).

The following tools are currently available:

- [`pds4_create_xml_index`](https://rms-pds4indextools.readthedocs.io/en/latest/pds4_create_xml_index.html):
  A command-line program to scrape information from a series of PDS4 XML labels, usually
  in a single collection, and generate a summary index file.
- [`pds4_create_collection_index`](https://rms-pds4indextools.readthedocs.io/en/latest/pds4_create_collection_index.html):
  A command-line program to create collection products for collections of PDS4 XML labels.

# Installation

`pds4indextools` is available via the `rms-pds4indextools` package on PyPI and
can be installed with:

```sh
pip install rms-pds4indextools
```

Note that this will install `pds4indextools` into your current system Python, or into your
currently activated virtual environment (venv), if any. You may also install using `pipx`,
which will isolate the installation from your system Python without requiring the creation
of a virtual environment. To install `pipx`, please see the [installation
instructions](https://pipx.pypa.io/stable/installation/). Once `pipx` is available, you
may install `pds4indextools` with:

```sh
pipx install rms-pds4indextools
```

# Getting Started With [`pds4_create_xml_index`](https://rms-pds4indextools.readthedocs.io/en/latest/pds4_create_xml_index.html)

Once `pds4indextools` has been installed, you may access the
[`pds4_create_xml_index`](https://rms-pds4indextools.readthedocs.io/en/latest/pds4_create_xml_index.html)
program directly from the command line.

The simplest use scrapes all XML labels from a collection and generates an index file:

```sh
pds4_create_xml_index <collection_dir> "**/*.xml"
```

Many options are available to customize the scraping and generation process, including
limiting which XML elements are scraped, changing the format of the resulting index file,
and generating a PDS4-compliant label. A summary of available options is available
by typing:

```sh
pds4_create_xml_index --help
```

Complete documentation is available [here](https://rms-pds4indextools.readthedocs.io/en/latest/pds4_create_xml_index.html)


# Getting Started With [`pds4_create_collection_index`](https://rms-pds4indextools.readthedocs.io/en/latest/pds4_create_collection_index.html)

Once `pds4indextools` has been installed, you may access the
[`pds4_create_collection_index`](https://rms-pds4indextools.readthedocs.io/en/latest/pds4_create_collection_index.html)
program directly from the command line.

The simplest use scrapes all XML labels from a collection and generates a collection product:

```sh
pds4_create_collection_index <collection_dir> --bundle bundle_name --collection collection_name
```

This will generate a collection product in the given collection directory. Full
instructions on usage can be found here:

```sh
pds4_create_collection_index --help
```

Complete documentation is available [here](https://rms-pds4indextools.readthedocs.io/en/latest/pds4_create_xml_index.html)


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
