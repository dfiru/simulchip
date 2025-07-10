"""Platform-specific utilities and input handling.

This module provides platform-independent abstractions for terminal operations
and user input handling.
"""

# Standard library imports
import sys
from typing import Protocol, runtime_checkable


@runtime_checkable
class InputHandler(Protocol):
    """Protocol for input handling implementations."""

    def get_char(self) -> str:
        """Get a single character from input."""
        ...


class UnixInputHandler:
    """Input handler for Unix-like systems (Linux, macOS)."""

    def get_char(self) -> str:
        """Get a single character from stdin without pressing enter."""
        # Standard library imports
        import termios
        import tty

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            char = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return char


class WindowsInputHandler:
    """Input handler for Windows systems."""

    def get_char(self) -> str:
        """Get a single character from stdin without pressing enter."""
        # Standard library imports
        import msvcrt

        char_bytes = msvcrt.getch()  # type: ignore
        return (
            char_bytes.decode("utf-8")
            if isinstance(char_bytes, bytes)
            else str(char_bytes)
        )


def get_input_handler() -> InputHandler:
    """Get appropriate input handler for current platform.

    Returns:
        InputHandler instance for the current platform
    """
    if sys.platform == "win32":
        return WindowsInputHandler()
    else:
        return UnixInputHandler()


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


# Global input handler instance (lazy-loaded)
_input_handler: InputHandler | None = None


def getch() -> str:
    """Get a single character from stdin without pressing enter.

    This is a convenience function that uses the platform-appropriate handler.

    Returns:
        Single character string
    """
    global _input_handler
    if _input_handler is None:
        _input_handler = get_input_handler()
    return _input_handler.get_char()
