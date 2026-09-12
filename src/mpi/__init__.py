"""Manufacturing Process & Quality Intelligence."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("manufacturing-process-intelligence")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = ["__version__"]
