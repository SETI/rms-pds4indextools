Installation
============

``rms-pds4indextools`` is distributed on PyPI and installs the
``pds4indextools`` package along with the ``pds4_create_xml_index``
command-line program.

Installing from PyPI
--------------------

Install the runtime package with::

    pip install rms-pds4indextools

To also install the test and lint stack (pytest, ruff, mypy, and the other
tools exercised by ``scripts/run-all-checks.sh``), request the ``dev``
extra::

    pip install "rms-pds4indextools[dev]"

To build this documentation locally (Sphinx plus the ReadTheDocs theme and
the Mermaid and MyST extensions), request the ``docs`` extra::

    pip install "rms-pds4indextools[docs]"

The two extras may be combined as ``"rms-pds4indextools[dev,docs]"``.

Supported Python versions
-------------------------

The package supports CPython 3.10 through 3.13 on the three major desktop
operating systems.

===========  =====  =====  =======
Python       Linux  macOS  Windows
===========  =====  =====  =======
3.10         yes    yes    yes
3.11         yes    yes    yes
3.12         yes    yes    yes
3.13         yes    yes    yes
===========  =====  =====  =======

Runtime dependencies
--------------------

Installing the package pulls in the following runtime dependencies. Pinned
floors are shown where the project declares one; the remaining packages
track their latest compatible release.

.. list-table::
   :header-rows: 1
   :widths: 22 18 60

   * - Distribution
     - Version floor
     - Purpose
   * - lxml
     - (latest)
     - XML label parsing; see :mod:`lxml`.
   * - pyyaml
     - (latest)
     - Configuration-file loading.
   * - pydantic
     - >= 2
     - Configuration schema and validation.
   * - rms-pdstemplate
     - >= 2.4
     - PDS4 label-template rendering.
   * - requests
     - (latest)
     - Fetching XSD schemas over HTTP; see :mod:`requests`.
   * - requests-file
     - (latest)
     - The ``file://`` transport for local schemas.
   * - platformdirs
     - (latest)
     - Locating the per-user schema cache directory.
   * - tqdm
     - (latest)
     - Optional progress bars during scraping.

System dependencies
-------------------

The ``lxml`` dependency links against the ``libxml2`` and ``libxslt`` C
libraries. On Linux and macOS these libraries must be present for the
wheel to import; most distributions provide them through the system package
manager (for example ``apt install libxml2 libxslt`` or the Homebrew
``libxml2`` and ``libxslt`` formulae). On Windows the published ``lxml``
wheel bundles its own copies, so no extra system packages are required.

Verifying the installation
--------------------------

Confirm that the console script is on the path and reports its version::

    pds4_create_xml_index --version

A successful install prints ``pds4_create_xml_index`` followed by the
installed version string.
