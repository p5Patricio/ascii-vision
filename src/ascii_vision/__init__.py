"""ASCII Vision core engine package."""

try:
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version as _version

    try:
        __version__ = _version("ascii-vision")
    except PackageNotFoundError:  # running from a source tree that was never installed
        __version__ = "0.0.0+unknown"
except Exception:  # pragma: no cover - extremely defensive
    __version__ = "0.0.0+unknown"
