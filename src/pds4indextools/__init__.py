"""Tools for generating index files and PDS4 labels from PDS4 XML labels."""

from pds4indextools._logging import library_setup, module_logger
from pds4indextools._version import __version__

__all__ = ['__version__', 'module_logger']

library_setup()
