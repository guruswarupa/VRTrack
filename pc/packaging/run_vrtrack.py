"""PyInstaller entry point (keeps the package's relative imports working when frozen)."""
import sys

from vrtrack.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
