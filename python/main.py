#!/usr/bin/env python3
"""
Main entry point for Pangea Net Python AI.
"""
import sys
from pathlib import Path

# Add src to path (absolute path)
SCRIPT_DIR = Path(__file__).resolve().parent
SRC_DIR = SCRIPT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

from cli import cli  # noqa: E402

if __name__ == "__main__":
    cli()
