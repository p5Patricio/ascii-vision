"""PyInstaller entry point for the ascii-vision command-line tool."""

import sys

from ascii_vision.cli import main

if __name__ == "__main__":
    sys.exit(main())
