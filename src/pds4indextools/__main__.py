"""Entry point for ``python -m pds4indextools``.

Delegates to :func:`pds4indextools.cli.main` and propagates its integer
return value to :func:`sys.exit`.
"""

import sys

from pds4indextools.cli import main

if __name__ == '__main__':
    sys.exit(main())
