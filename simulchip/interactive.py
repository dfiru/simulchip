"""Interactive interface state management.

This module provides state management and business logic for interactive
terminal interfaces.
"""

# Standard library imports
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Dict, Optional, Tuple


class KeyAction(Enum):
    """Standard key actions for interactive interfaces."""

    # Navigation
    UP = "up"
    DOWN = "down"
    PAGE_UP = "page_up"
    PAGE_DOWN = "page_down"
    TOP = "top"
    BOTTOM = "bottom"

    # Selection/Editing
    SELECT = "select"
    TOGGLE = "toggle"
    INCREMENT = "increment"
    DECREMENT = "decrement"
    SET_VALUE = "set_value"
    RESET = "reset"

    # Text operations
    FILTER_ADD_CHAR = "filter_add_char"
    FILTER_BACKSPACE = "filter_backspace"
    FILTER_CLEAR = "filter_clear"

    # Interface control
    SAVE_AND_EXIT = "save_and_exit"
    CANCEL = "cancel"
    TOGGLE_MODE = "toggle_mode"
    HELP = "help"

    # Special
    UNKNOWN = "unknown"


@dataclass
class InteractiveState:
    """State for interactive interfaces."""

    selected_index: int = 0
    filter_text: str = ""
    mode_flags: Optional[Dict[str, bool]] = None
    viewport_start: int = 0
    viewport_end: int = 0
    total_items: int = 0

    def __post_init__(self) -> None:
        """Initialize mode flags if not provided."""
        if self.mode_flags is None:
            self.mode_flags = {}

    def reset_selection(self) -> None:
        """Reset selection to beginning."""
        self.selected_index = 0

    def update_viewport(self, start: int, end: int) -> None:
        """Update viewport boundaries."""
        self.viewport_start = start
        self.viewport_end = end

    def set_filter(self, text: str, reset_selection: bool = True) -> None:
        """Set filter text and optionally reset selection."""
        self.filter_text = text
        if reset_selection:
            self.reset_selection()

    def toggle_mode(self, mode_name: str) -> bool:
        """Toggle a mode flag and return new state."""
        if self.mode_flags is None:
            self.mode_flags = {}
        current = self.mode_flags.get(mode_name, False)
        self.mode_flags[mode_name] = not current
        return not current


class KeyMapper:
    """Maps keyboard input to actions."""

    # Standard key mappings
    ESCAPE_SEQUENCES = {
        # Arrow keys (ESC[X format)
        "\x1b[A": KeyAction.UP,
        "\x1b[B": KeyAction.DOWN,
        "\x1b[C": KeyAction.INCREMENT,  # Right arrow
        "\x1b[D": KeyAction.DECREMENT,  # Left arrow
        "\x1b[5~": KeyAction.PAGE_UP,  # Page Up
        "\x1b[6~": KeyAction.PAGE_DOWN,  # Page Down
    }

    SINGLE_CHARS = {
        # Vim-style navigation
        "j": KeyAction.UP,
        "k": KeyAction.DOWN,
        "g": KeyAction.TOP,
        "G": KeyAction.BOTTOM,
        # Control characters
        "\x15": KeyAction.PAGE_UP,  # Ctrl+U
        "\x04": KeyAction.PAGE_DOWN,  # Ctrl+D
        "\x03": KeyAction.SAVE_AND_EXIT,  # Ctrl+C
        # Common actions
        " ": KeyAction.TOGGLE,  # Space
        "\r": KeyAction.SELECT,  # Enter
        "\n": KeyAction.SELECT,  # Enter (alternative)
        "q": KeyAction.SAVE_AND_EXIT,
        "\x1b": KeyAction.SAVE_AND_EXIT,  # Escape (when not part of sequence)
        # Editing
        "\x7f": KeyAction.FILTER_BACKSPACE,  # Backspace
        "\b": KeyAction.FILTER_BACKSPACE,  # Backspace (alternative)
        # Number keys (for setting values)
        "0": KeyAction.RESET,
        "1": KeyAction.SET_VALUE,
        "2": KeyAction.SET_VALUE,
        "3": KeyAction.SET_VALUE,
        "4": KeyAction.SET_VALUE,
        "5": KeyAction.SET_VALUE,
        "6": KeyAction.SET_VALUE,
        "7": KeyAction.SET_VALUE,
        "8": KeyAction.SET_VALUE,
        "9": KeyAction.SET_VALUE,
        # Mode toggles
        "e": KeyAction.TOGGLE_MODE,
        "E": KeyAction.TOGGLE_MODE,
        # Help
        "?": KeyAction.HELP,
        "h": KeyAction.HELP,
    }

    def __init__(self, custom_mappings: Optional[Dict[str, KeyAction]] = None):
        """Initialize with optional custom key mappings."""
        self.custom_mappings = custom_mappings or {}

    def map_key(self, key: str) -> Tuple[KeyAction, Optional[str]]:
        """Map a key to an action and optional value.

        Args:
            key: The key character(s) to map

        Returns:
            Tuple of (action, value) where value is used for SET_VALUE actions
        """
        # Check custom mappings first
        if key in self.custom_mappings:
            action = self.custom_mappings[key]
            return self._get_action_and_value(action, key)

        # Check escape sequences
        if key in self.ESCAPE_SEQUENCES:
            action = self.ESCAPE_SEQUENCES[key]
            return self._get_action_and_value(action, key)

        # Check single characters
        if key in self.SINGLE_CHARS:
            action = self.SINGLE_CHARS[key]
            return self._get_action_and_value(action, key)

        # Handle printable characters as filter input
        if key.isprintable() and len(key) == 1:
            return KeyAction.FILTER_ADD_CHAR, key

        return KeyAction.UNKNOWN, None

    def _get_action_and_value(
        self, action: KeyAction, key: str
    ) -> Tuple[KeyAction, Optional[str]]:
        """Get action and extract value for SET_VALUE actions."""
        if action == KeyAction.SET_VALUE and key.isdigit():
            return action, key
        return action, None


def process_navigation_action(
    state: InteractiveState, action: KeyAction, total_items: int, page_size: int = 10
) -> bool:
    """Process navigation actions and update state.

    Args:
        state: Current interactive state
        action: Navigation action to process
        total_items: Total number of items
        page_size: Number of items per page

    Returns:
        True if state was modified
    """
    if total_items == 0:
        state.selected_index = 0
        return True

    old_index = state.selected_index

    if action == KeyAction.UP:
        state.selected_index = max(0, state.selected_index - 1)
    elif action == KeyAction.DOWN:
        state.selected_index = min(total_items - 1, state.selected_index + 1)
    elif action == KeyAction.PAGE_UP:
        state.selected_index = max(0, state.selected_index - page_size)
    elif action == KeyAction.PAGE_DOWN:
        state.selected_index = min(total_items - 1, state.selected_index + page_size)
    elif action == KeyAction.TOP:
        state.selected_index = 0
    elif action == KeyAction.BOTTOM:
        state.selected_index = max(0, total_items - 1)

    return state.selected_index != old_index


def process_filter_action(
    state: InteractiveState,
    action: KeyAction,
    value: Optional[str] = None,
    reset_selection_on_change: bool = True,
) -> bool:
    """Process filter actions and update state.

    Args:
        state: Current interactive state
        action: Filter action to process
        value: Value for FILTER_ADD_CHAR actions
        reset_selection_on_change: Whether to reset selection when filter changes

    Returns:
        True if state was modified
    """
    old_filter = state.filter_text

    if action == KeyAction.FILTER_ADD_CHAR and value:
        state.filter_text += value
    elif action == KeyAction.FILTER_BACKSPACE:
        if state.filter_text:
            state.filter_text = state.filter_text[:-1]
    elif action == KeyAction.FILTER_CLEAR:
        state.filter_text = ""

    # Reset selection if filter changed and option is enabled
    if state.filter_text != old_filter and reset_selection_on_change:
        state.reset_selection()
        return True

    return state.filter_text != old_filter


class InteractiveController:
    """Controller for interactive interfaces."""

    def __init__(
        self,
        key_mapper: Optional[KeyMapper] = None,
        page_size: int = 10,
        reset_selection_on_filter_change: bool = True,
    ):
        """Initialize controller with configuration."""
        self.key_mapper = key_mapper or KeyMapper()
        self.page_size = page_size
        self.reset_selection_on_filter_change = reset_selection_on_filter_change
        self.state = InteractiveState()

    def process_key(
        self,
        key: str,
        total_items: int,
        custom_handlers: Optional[Dict[KeyAction, Callable]] = None,
    ) -> Tuple[KeyAction, bool]:
        """Process a key press and update state.

        Args:
            key: The key that was pressed
            total_items: Total number of items in the interface
            custom_handlers: Optional custom action handlers

        Returns:
            Tuple of (action, state_changed)
        """
        action, value = self.key_mapper.map_key(key)
        state_changed = False

        # Handle custom actions first
        if custom_handlers and action in custom_handlers:
            try:
                custom_handlers[action](self.state, value)
                state_changed = True
            except Exception:
                # Ignore custom handler errors
                pass

        # Handle standard navigation actions
        elif action in {
            KeyAction.UP,
            KeyAction.DOWN,
            KeyAction.PAGE_UP,
            KeyAction.PAGE_DOWN,
            KeyAction.TOP,
            KeyAction.BOTTOM,
        }:
            state_changed = process_navigation_action(
                self.state, action, total_items, self.page_size
            )

        # Handle filter actions
        elif action in {
            KeyAction.FILTER_ADD_CHAR,
            KeyAction.FILTER_BACKSPACE,
            KeyAction.FILTER_CLEAR,
        }:
            state_changed = process_filter_action(
                self.state, action, value, self.reset_selection_on_filter_change
            )

        # Update total items count
        if self.state.total_items != total_items:
            self.state.total_items = total_items
            state_changed = True

        return action, state_changed
