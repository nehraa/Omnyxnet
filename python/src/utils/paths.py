"""
Path utilities for finding project root and schema files.
Handles cross-directory imports and absolute paths.
"""

from pathlib import Path


def find_project_root(start_path: Path = None) -> Path:
    """
    Find the project root directory (WGT/).

    Looks for markers like:
    - go/ directory
    - python/ directory
    - README.md

    Args:
        start_path: Starting path (defaults to current file's directory)

    Returns:
        Path to project root
    """
    if start_path is None:
        # Start from this file's location
        start_path = Path(__file__).resolve().parent.parent.parent.parent

    current = Path(start_path).resolve()

    # Look for project markers
    markers = ["go", "python", "README.md", "go/go.mod"]

    # Go up the directory tree
    for _ in range(10):  # Max 10 levels up
        # Check if we're at project root
        has_markers = all((current / marker).exists() for marker in markers[:2])
        if has_markers:
            return current
        parent = current.parent
        if parent == current:  # Reached filesystem root
            break
        current = parent

    # Fallback: assume we're in WGT/python/src/utils, so go up 3 levels
    return Path(__file__).resolve().parent.parent.parent.parent


def get_schema_path() -> Path:
    """
    Get absolute path to schema.capnp file.

    Returns:
        Absolute path to python/schema.capnp
    """
    project_root = find_project_root()
    schema_path = project_root / "python" / "schema.capnp"
    return schema_path


def get_go_schema_path() -> str:
    """
    Get absolute path to schema.capnp as string.

    Returns:
        Absolute path string to schema.capnp
    """
    return str(get_schema_path())


# Project root (cached)
_PROJECT_ROOT = None


def get_project_root() -> Path:
    """Get cached project root."""
    global _PROJECT_ROOT
    if _PROJECT_ROOT is None:
        _PROJECT_ROOT = find_project_root()
    return _PROJECT_ROOT
