"""Platform-specific utilities and input handling.

This module provides platform-independent abstractions for terminal operations
and user input handling.
"""

# Standard library imports
import sys
import typer


def is_interactive_terminal() -> bool:
    """Check if running in an interactive terminal.

    Returns:
        True if stdin is a TTY (interactive terminal)
    """
    return sys.stdin.isatty()


def get_platform_name() -> str:
    """Get platform name for logging/debugging.

    Returns:
        Platform name string
    """
    return sys.platform


def getch() -> str:
    """Get a single character from stdin without pressing enter.

    Uses typer's built-in cross-platform getchar() function.

    Returns:
        Single character string or escape sequence
    """
    return typer.getchar()
