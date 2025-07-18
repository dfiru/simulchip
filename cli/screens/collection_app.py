"""Collection management app with screen-based navigation."""

from pathlib import Path
from typing import Optional
import logging
from datetime import datetime

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Static, DataTable, RichLog, Input, Log, Button
from textual.widget import Widget
from textual.reactive import reactive
from textual import events
from textual.message import Message

from simulchip import __version__
from simulchip.api.netrunnerdb import NetrunnerDBAPI
from simulchip.collection.manager import CollectionManager

# Set up file logging
logging.basicConfig(
    filename='simulchip_debug.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BaseScreen(Screen):
    """Base screen with common log panel functionality."""
    
    CSS = """
    .log-panel {
        dock: bottom;
        height: 10;
        background: #181825;         /* Mantle - darker than base */
        border: solid #45475a;       /* Surface1 */
        padding: 0 1;
        display: none;
        color: #cdd6f4;              /* Text */
    }
    
    .log-panel-visible {
        display: block;
    }
    """
    
    def compose(self) -> ComposeResult:
        """Override in subclasses to add screen-specific content."""
        # Subclasses should yield their widgets and then call super().compose()
        # to add the log panel at the end
        yield RichLog(id="log-panel", classes="log-panel", wrap=True, highlight=True, markup=True)
    
    def on_mount(self) -> None:
        """Check app's log state when screen mounts."""
        if hasattr(self.app, 'log_visible') and self.app.log_visible:
            self.toggle_log_panel(True)
    
    def toggle_log_panel(self, visible: bool) -> None:
        """Toggle the log panel visibility."""
        try:
            log_panel = self.query_one("#log-panel", RichLog)
            if visible:
                log_panel.add_class("log-panel-visible")
                logger.info(f"=== {self.__class__.__name__} log panel shown ===")
            else:
                log_panel.remove_class("log-panel-visible")
                logger.info(f"=== {self.__class__.__name__} log panel hidden ===")
        except Exception as e:
            logger.error(f"Error toggling log panel: {e}", exc_info=True)


class FilterableDataTable(Widget):
    """A reusable widget that combines a filter input with a DataTable."""
    
    CSS = """
    FilterableDataTable {
        layout: vertical;
        height: 1fr;
    }
    
    .filter-input-container {
        height: 0;                   /* Start with no height */
        margin: 0 1;
        border: solid #45475a;       /* Surface1 */
        background: #313244;         /* Surface0 */
        color: #cdd6f4;              /* Text */
        overflow: hidden;            /* Hide content when height is 0 */
        transition: height 0.2s;     /* Smooth transition */
    }
    
    .filter-input-container Input {
        background: #313244;         /* Surface0 */
        border: none;
    }
    
    .filter-input-container Input:focus {
        border: none;
    }
    
    FilterableDataTable DataTable {
        height: 1fr;
        border: solid #45475a;       /* Surface1 */
        background: #1e1e2e;         /* Base */
        overflow-y: auto;
    }
    
    FilterableDataTable DataTable > .datatable--header {
        background: #313244;         /* Surface0 */
        color: #cba6f7;              /* Mauve */
        text-style: bold;
    }
    
    FilterableDataTable DataTable > .datatable--cursor {
        background: #cba6f7 20%;     /* Mauve with transparency */
    }
    
    FilterableDataTable DataTable > .datatable--odd-row {
        background: #181825;         /* Mantle */
    }
    
    FilterableDataTable DataTable > .datatable--even-row {
        background: #1e1e2e;         /* Base */
    }
    """
    
    class FilterChanged(Message):
        """Message sent when filter text changes."""
        def __init__(self, filter_text: str) -> None:
            self.filter_text = filter_text
            super().__init__()
    
    def __init__(self, placeholder: str = "Type to filter...", table_id: str = "data-table"):
        super().__init__()
        self.placeholder = placeholder
        self.table_id = table_id
        self.filter_input = None
        self.filter_text = ""
        # Create the table here so it's available before compose
        self.table = DataTable(id=self.table_id, zebra_stripes=True, show_header=True)
    
    def compose(self) -> ComposeResult:
        """Create the filterable table UI."""
        # Filter input (initially hidden) - on top
        with Container(classes="filter-input-container", id="filter-container"):
            self.filter_input = Input(placeholder=self.placeholder, id="filter-input")
            yield self.filter_input
        
        # DataTable directly
        yield self.table
    
    @property
    def data_table(self) -> DataTable:
        """Get the DataTable widget."""
        return self.table
    
    def show_filter(self) -> None:
        """Show and focus the filter input."""
        logger.info("=== FilterableDataTable.show_filter called ===")
        filter_container = self.query_one("#filter-container", Container)
        filter_container.styles.height = 3  # Set height to show
        if self.filter_input:
            logger.info(f"Setting focus to filter_input: {self.filter_input}")
            self.filter_input.focus()
            # Set value to current filter text if any
            if self.filter_text:
                self.filter_input.value = self.filter_text
    
    async def clear_filter(self) -> None:
        """Clear the filter and hide input."""
        self.filter_text = ""
        if self.filter_input:
            self.filter_input.value = ""
        filter_container = self.query_one("#filter-container", Container)
        filter_container.styles.height = 0  # Set height to 0 to hide
        self.post_message(self.FilterChanged(""))
        # Focus the table after clearing filter
        self.table.focus()
    
    async def on_key(self, event: events.Key) -> None:
        """Handle key events."""
        # Check if filter input has focus
        focused = self.app.focused
        if focused and isinstance(focused, Input) and focused == self.filter_input:
            # Only handle specific navigation keys
            if event.key == "escape":
                # Escape clears the filter
                await self.clear_filter()
                event.stop()
                return
            elif event.key in ("tab", "enter", "down"):
                # Tab, Enter, or Down moves focus to the table
                self.table.focus()
                event.stop()
                return
            # For typing keys, don't process them here but prevent parent handling
            # The Input widget will handle these keys naturally
            return
    
    async def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes for filtering."""
        logger.info(f"=== FilterableDataTable.on_input_changed: {event.value} ===")
        if event.input == self.filter_input:
            self.filter_text = event.value
            self.post_message(self.FilterChanged(event.value))
    
    def on_mount(self) -> None:
        """When the widget is mounted, ensure DataTable starts at top."""
        # Force the DataTable to start at the top
        self.table.scroll_to(0, 0, animate=False)




class WelcomeScreen(BaseScreen):
    """Welcome screen with instructions."""
    
    CSS = """
    .welcome-container {
        align: center middle;
        height: 100%;
    }
    
    .welcome-content {
        width: auto;
        height: auto;
        border: solid #cba6f7;       /* Mauve */
        padding: 2 4;
        background: #313244;         /* Surface0 */
        color: #cdd6f4;              /* Text */
    }
    """
    
    BINDINGS = [
        Binding("p", "switch_to_packs", "Packs"),
        Binding("c", "switch_to_cards", "Cards"),
        Binding("s", "switch_to_stats", "Stats"),
        Binding("o", "toggle_log", "Log"),
        Binding("q,escape", "quit", "Quit"),
    ]
    
    def compose(self) -> ComposeResult:
        """Create the welcome screen UI."""
        yield Header()
        with Container(classes="welcome-container"):
            yield Static(
                f"""[bold #cba6f7]
    ███████╗██╗███╗   ███╗██╗   ██╗██╗      ██████╗██╗  ██╗██╗██████╗ 
    ██╔════╝██║████╗ ████║██║   ██║██║     ██╔════╝██║  ██║██║██╔══██╗
    ███████╗██║██╔████╔██║██║   ██║██║     ██║     ███████║██║██████╔╝
    ╚════██║██║██║╚██╔╝██║██║   ██║██║     ██║     ██╔══██║██║██╔═══╝ 
    ███████║██║██║ ╚═╝ ██║╚██████╔╝███████╗╚██████╗██║  ██║██║██║     
    ╚══════╝╚═╝╚═╝     ╚═╝ ╚═════╝ ╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝╚═╝     
[/bold #cba6f7]

[bold #f9e2af]Welcome to Simulchip Collection Manager![/bold #f9e2af]
[dim]Version {__version__}[/dim]

Navigate with keyboard shortcuts:
  • [#89dceb]p[/] - Manage Packs
  • [#89dceb]c[/] - Manage Cards  
  • [#89dceb]s[/] - View Stats
  • [#89dceb]o[/] - Toggle Log (from any screen)
  • [#89dceb]ctrl+s[/] - Save Collection
  • [#89dceb]q[/] - Quit

Your collection is automatically loaded.""",
                classes="welcome-content"
            )
        yield Footer()
        yield from super().compose()  # Add log panel
    
    def action_switch_to_packs(self) -> None:
        """Switch to packs screen."""
        self.app.push_screen("packs")
    
    def action_switch_to_cards(self) -> None:
        """Switch to cards screen."""
        self.app.push_screen("cards")
    
    def action_switch_to_stats(self) -> None:
        """Switch to stats screen."""
        self.app.push_screen("stats")
    
    def action_toggle_log(self) -> None:
        """Toggle log panel for this screen."""
        logger.info(f"=== {self.__class__.__name__} toggle_log ===")
        self.app.log_visible = not self.app.log_visible
        self.toggle_log_panel(self.app.log_visible)
        status = "opened" if self.app.log_visible else "closed"
        self.app.notify(f"Log panel {status}")
    
    def action_quit(self) -> None:
        """Quit the app."""
        self.app.exit("quit")
    


class PacksScreen(BaseScreen):
    """Screen for managing pack collection."""
    
    CSS = BaseScreen.CSS + """
    .title {
        height: 1;
        text-align: center;
        background: #45475a;         /* Surface1 */
        color: #cdd6f4;              /* Text */
        content-align: center middle;
        text-style: bold;
    }
    
    .status-bar {
        height: 1;
        background: #313244;         /* Surface0 */
        color: #a6adc8;              /* Subtext0 */
        text-align: center;
        content-align: center middle;
    }
    
    PacksScreen {
        layout: vertical;
    }
    
    PacksScreen FilterableDataTable {
        height: 1fr;
        align: left top;
    }
    """
    
    BINDINGS = [
        Binding("w", "switch_to_welcome", "Welcome"),
        Binding("c", "switch_to_cards", "Cards"),
        Binding("s", "switch_to_stats", "Stats"),
        Binding("o", "toggle_log", "Log"),
        Binding("space", "toggle_pack", "Toggle", show=False),
        Binding("m", "toggle_mine", "Mine"),
        Binding("/", "start_filter", "Filter"),
        Binding("ctrl+s", "save", "Save"),
        Binding("q", "quit", "Quit"),
    ]
    
    def __init__(self, collection_manager: CollectionManager, api: NetrunnerDBAPI):
        super().__init__()
        self.collection_manager = collection_manager
        self.api = api
        self.pack_codes = []  # Track pack codes by row index
        self.show_mine_only = False  # Filter state
        self.filter_text = ""  # Search filter text
        self.filterable_table = None  # Will be set in compose
    
    def compose(self) -> ComposeResult:
        """Create the packs screen UI."""
        yield Header(show_clock=True, classes="header")
        yield Static("Packs Management", classes="title")
        
        # Use the FilterableDataTable widget
        self.filterable_table = FilterableDataTable(
            placeholder="Type to filter packs...",
            table_id="pack-table"
        )
        self.filterable_table.data_table.add_columns("Status", "Code", "Name", "Cycle", "Date")
        yield self.filterable_table
        
        yield Static(
            "nav: (w)elcome (c)ards (s)tats • Space: toggle • (m)ine • /: filter • Ctrl+S: save • q: quit",
            classes="status-bar",
            id="status"
        )
        yield Footer()
        yield from super().compose()  # Add log panel
    
    async def on_mount(self) -> None:
        """Initialize when the screen is mounted."""
        super().on_mount()  # Initialize log panel state
        await self.populate_table()
        # Schedule a scroll fix after the screen is fully rendered
        self.set_timer(0.1, self._fix_table_scroll)
    
    def _fix_table_scroll(self) -> None:
        """Fix table scroll position after rendering."""
        table = self.filterable_table.data_table
        # Force scroll to absolute top
        table.scroll_to(0, 0, animate=False)
        if len(self.pack_codes) > 0:
            table.move_cursor(row=0)
    
    async def populate_table(self) -> None:
        """Populate the pack table with data."""
        table = self.filterable_table.data_table
        table.clear()
        self.pack_codes.clear()
        
        # Get all packs
        all_packs = self.api.get_all_packs()
        
        # Apply filters
        filtered_packs = []
        
        if self.show_mine_only:
            # Show only owned packs
            filtered_packs = [p for p in all_packs if self.collection_manager.has_pack(p["code"])]
        else:
            filtered_packs = all_packs
        
        # Apply text filter if active
        if self.filter_text:
            search_lower = self.filter_text.lower()
            filtered_packs = [
                p for p in filtered_packs
                if search_lower in p.get("name", "").lower() or
                   search_lower in p.get("code", "").lower() or
                   search_lower in p.get("cycle", "").lower()
            ]
        
        # Sort by date (newest first)
        filtered_packs.sort(key=lambda p: p.get("date_release", "") or "0000", reverse=True)
        
        # Add rows
        for pack in filtered_packs:
            pack_code = pack["code"]
            self.pack_codes.append(pack_code)
            
            if self.collection_manager.has_pack(pack_code):
                owned_symbol = "[#a6e3a1]✓ Owned[/]"
            else:
                owned_symbol = "[#6c7086]○ Not Owned[/]"
            
            table.add_row(
                owned_symbol,
                pack["code"],
                pack.get("name", "Unknown"),
                pack.get("cycle", "Unknown"),
                pack.get("date_release", "Unknown")
            )
        
        # Update status bar with filter state
        status_parts = []
        if self.show_mine_only:
            status_parts.append("(m)ine filter ON")
        if self.filter_text:
            status_parts.append(f"filter: '{self.filter_text}'")
        
        if status_parts:
            status_text = f"nav: (w)elcome (c)ards (s)tats • {' • '.join(status_parts)} • Space: toggle • q: quit"
        else:
            status_text = "nav: (w)elcome (c)ards (s)tats • Space: toggle • (m)ine • /: filter • Ctrl+S: save • q: quit"
        
        self.query_one("#status", Static).update(status_text)
        
        # Scroll to top and move cursor to first row after populating
        if len(self.pack_codes) > 0:
            table.move_cursor(row=0)
            # Force scroll to the very top
            table.scroll_to(0, 0, animate=False)
            # Also try scrolling the widget itself
            self.filterable_table.scroll_to(0, 0, animate=False)
            # Add another attempt with a slight delay
            self.set_timer(0.01, lambda: table.scroll_to(0, 0, animate=False))
        
        # Only focus the table if no input is currently focused
        if not (self.app.focused and isinstance(self.app.focused, Input)):
            table.focus()
    
    def action_toggle_pack(self) -> None:
        """Toggle the selected pack's ownership status."""
        table = self.filterable_table.data_table
        if table.cursor_row is not None and table.cursor_row < len(self.pack_codes):
            # Get the pack code from our tracked list
            pack_code = self.pack_codes[table.cursor_row]
            
            # Toggle pack ownership
            if self.collection_manager.has_pack(pack_code):
                self.collection_manager.remove_pack(pack_code)
                new_status = "[#6c7086]○ Not Owned[/]"
            else:
                self.collection_manager.add_pack(pack_code)
                new_status = "[#a6e3a1]✓ Owned[/]"
            
            # If in mine mode and pack should be removed from view, refresh the table
            if self.show_mine_only and new_status == "[#6c7086]○ Not Owned[/]":
                self.run_worker(self.populate_table)
            else:
                # Otherwise just update the table cell
                table.update_cell_at((table.cursor_row, 0), new_status)
    
    def action_save(self) -> None:
        """Save the collection."""
        logger.info("=== Save action triggered ===")
        try:
            log_panel = self.query_one("#log-panel", RichLog)
            log_panel.write("[#89dceb]Save action triggered[/]")
        except:
            logger.warning("Could not write to log panel")
            
        try:
            self.collection_manager.save_collection()
            self.notify("Collection saved successfully")
            logger.info("Collection saved successfully")
            try:
                log_panel = self.query_one("#log-panel", RichLog)
                log_panel.write("[#a6e3a1]Collection saved successfully[/]")
            except:
                pass
        except Exception as e:
            self.notify(f"Error saving: {e}", severity="error")
            logger.error(f"Error saving: {e}", exc_info=True)
            try:
                log_panel = self.query_one("#log-panel", RichLog)
                log_panel.write(f"[#f38ba8]Error saving: {e}[/]")
            except:
                pass
    
    def action_switch_to_welcome(self) -> None:
        """Switch to welcome screen."""
        self.app.switch_screen("welcome")
    
    def action_switch_to_cards(self) -> None:
        """Switch to cards screen."""
        self.app.push_screen("cards")
    
    def action_switch_to_stats(self) -> None:
        """Switch to stats screen."""
        self.app.push_screen("stats")
    
    def action_toggle_log(self) -> None:
        """Toggle log panel for this screen."""
        logger.info(f"=== {self.__class__.__name__} toggle_log ===")
        self.app.log_visible = not self.app.log_visible
        self.toggle_log_panel(self.app.log_visible)
        status = "opened" if self.app.log_visible else "closed"
        self.app.notify(f"Log panel {status}")
    
    def action_quit(self) -> None:
        """Quit the app."""
        self.app.exit("quit")
    
    def action_toggle_mine(self) -> None:
        """Toggle showing only owned packs."""
        self.show_mine_only = not self.show_mine_only
        logger.info(f"Mine filter toggled: {self.show_mine_only}")
        self.run_worker(self.populate_table)
    
    def action_start_filter(self) -> None:
        """Start filtering packs."""
        self.filterable_table.show_filter()
    
    async def on_filterable_data_table_filter_changed(self, message: FilterableDataTable.FilterChanged) -> None:
        """Handle filter changes from the FilterableDataTable."""
        self.filter_text = message.filter_text
        await self.populate_table()
    


class CardsScreen(BaseScreen):
    """Screen for managing card quantities."""
    
    CSS = BaseScreen.CSS + """
    .title {
        height: 1;
        text-align: center;
        background: #45475a;         /* Surface1 */
        color: #cdd6f4;              /* Text */
        content-align: center middle;
        text-style: bold;
    }
    
    .status-bar {
        height: 1;
        background: #313244;         /* Surface0 */
        color: #a6adc8;              /* Subtext0 */
        text-align: center;
        content-align: center middle;
    }
    
    CardsScreen {
        layout: vertical;
    }
    
    CardsScreen FilterableDataTable {
        height: 1fr;
        align: left top;
    }
    """
    
    BINDINGS = [
        Binding("w", "switch_to_welcome", "Welcome"),
        Binding("p", "switch_to_packs", "Packs"),
        Binding("s", "switch_to_stats", "Stats"),
        Binding("o", "toggle_log", "Log"),
        Binding("+,=", "increment_card", "Add"),
        Binding("-,_", "decrement_card", "Remove"),
        Binding("m", "toggle_mine", "Mine"),
        Binding("/", "focus_filter", "Filter", show=False),
        Binding("ctrl+s", "save", "Save"),
        Binding("q", "quit", "Quit"),
    ]
    
    def __init__(self, collection_manager: CollectionManager, api: NetrunnerDBAPI):
        super().__init__()
        self.collection_manager = collection_manager
        self.api = api
        self.card_codes = []  # Track card codes by row index
        self.show_mine_only = False  # Filter state
        self.filter_text = ""  # Search filter text
        self.filterable_table = None  # Will be set in compose
    
    def compose(self) -> ComposeResult:
        """Create the cards screen UI."""
        yield Header(show_clock=True)
        yield Static("Cards Management", classes="title")
        
        # Use the FilterableDataTable widget
        self.filterable_table = FilterableDataTable(
            placeholder="Type to filter cards...",
            table_id="card-table"
        )
        self.filterable_table.data_table.add_columns("Count", "Card", "Type", "Faction", "Pack")
        yield self.filterable_table
        
        yield Static(
            "nav: (w)elcome (p)acks (s)tats • +: add • -: remove • (m)ine • /: filter • Ctrl+S: save • q: quit",
            classes="status-bar",
            id="status"
        )
        yield Footer()
        yield from super().compose()  # Add log panel
    
    async def on_mount(self) -> None:
        """Initialize when the screen is mounted."""
        super().on_mount()  # Initialize log panel state
        await self.populate_card_table()
    
    async def populate_card_table(self) -> None:
        """Populate the card table with data."""
        table = self.filterable_table.data_table
        table.clear()
        self.card_codes.clear()
        
        # Get all cards
        all_cards = self.api.get_all_cards_list()
        
        # Apply filters
        filtered_cards = []
        
        if self.show_mine_only:
            # Show cards that are expected OR have count differences
            filtered_cards = []
            for card in all_cards:
                card_code = card["code"]
                expected = self.collection_manager.get_expected_card_count(card_code)
                owned = self.collection_manager.get_actual_card_count(card_code)
                # Include if expected > 0 OR owned != expected
                if expected > 0 or owned != expected:
                    filtered_cards.append(card)
        else:
            filtered_cards = all_cards
        
        # Apply text filter if active
        if self.filter_text:
            search_lower = self.filter_text.lower()
            filtered_cards = [
                c for c in filtered_cards
                if search_lower in c.get("title", "").lower() or
                   search_lower in c.get("type_code", "").lower() or
                   search_lower in c.get("faction_code", "").lower() or
                   search_lower in c.get("pack_code", "").lower()
            ]
        
        # Sort by name
        filtered_cards.sort(key=lambda c: c.get("title", ""))
        
        # Add rows
        for card in filtered_cards:
            card_code = card["code"]
            self.card_codes.append(card_code)
            
            owned = self.collection_manager.get_actual_card_count(card_code)
            expected = self.collection_manager.get_expected_card_count(card_code)
            
            table.add_row(
                f"[#cba6f7]{owned}[/] / [#a6adc8]{expected}[/]",
                card.get("title", "Unknown"),
                card.get("type_code", "Unknown"),
                card.get("faction_code", "Unknown"),
                card.get("pack_code", "Unknown")
            )
        
        # Update status bar with filter state
        status_parts = []
        if self.show_mine_only:
            status_parts.append("(m)ine filter ON")
        if self.filter_text:
            status_parts.append(f"filter: '{self.filter_text}'")
        
        if status_parts:
            status_text = f"nav: (w)elcome (p)acks (s)tats • {' • '.join(status_parts)} • +: add • -: remove • q: quit"
        else:
            status_text = "nav: (w)elcome (p)acks (s)tats • +: add • -: remove • (m)ine • /: filter • Ctrl+S: save • q: quit"
        
        self.query_one("#status", Static).update(status_text)
        
        # Scroll to top and move cursor to first row after populating
        if len(self.card_codes) > 0:
            table.move_cursor(row=0)
            # Force scroll to the very top
            table.scroll_to(0, 0, animate=False)
        
        # Only focus the table if no input is currently focused
        if not (self.app.focused and isinstance(self.app.focused, Input)):
            table.focus()
    
    def action_increment_card(self) -> None:
        """Increment the selected card count."""
        # Don't process if filter has focus
        if self.app.focused == self.filterable_table.filter_input:
            return
        logger.info("=== action_increment_card called ===")
        table = self.filterable_table.data_table
        if table.cursor_row is not None and table.cursor_row < len(self.card_codes):
            card_code = self.card_codes[table.cursor_row]
            card_name = table.get_cell_at((table.cursor_row, 1))
            logger.info(f"Incrementing card: {card_code} ({card_name})")
            
            # Add one card to actual count
            current_count = self.collection_manager.get_actual_card_count(card_code)
            self.collection_manager.set_card_count(card_code, current_count + 1)
            
            # Update the display
            new_count = self.collection_manager.get_actual_card_count(card_code)
            expected = self.collection_manager.get_expected_card_count(card_code)
            new_display = f"[#cba6f7]{new_count}[/] / [#a6adc8]{expected}[/]"
            table.update_cell_at((table.cursor_row, 0), new_display)
            logger.info(f"Updated table cell to: {new_display}")
            
            logger.info(f"Card {card_code} incremented to {new_count}")
        else:
            logger.warning(f"Cannot increment: cursor_row={table.cursor_row}, card_codes_len={len(self.card_codes)}")
    
    def action_decrement_card(self) -> None:
        """Decrement the selected card count."""
        # Don't process if filter has focus
        if self.app.focused == self.filterable_table.filter_input:
            return
        logger.info("=== action_decrement_card called ===")
        table = self.filterable_table.data_table
        if table.cursor_row is not None and table.cursor_row < len(self.card_codes):
            card_code = self.card_codes[table.cursor_row]
            card_name = table.get_cell_at((table.cursor_row, 1))
            logger.info(f"Decrementing card: {card_code} ({card_name})")
            
            # Remove one card from actual count (won't go below 0)
            current_count = self.collection_manager.get_actual_card_count(card_code)
            self.collection_manager.set_card_count(card_code, max(0, current_count - 1))
            
            # Update the display
            new_count = self.collection_manager.get_actual_card_count(card_code)
            expected = self.collection_manager.get_expected_card_count(card_code)
            new_display = f"[#cba6f7]{new_count}[/] / [#a6adc8]{expected}[/]"
            table.update_cell_at((table.cursor_row, 0), new_display)
            logger.info(f"Updated table cell to: {new_display}")
            
            logger.info(f"Card {card_code} decremented to {new_count}")
        else:
            logger.warning(f"Cannot decrement: cursor_row={table.cursor_row}, card_codes_len={len(self.card_codes)}")
    
    def action_save(self) -> None:
        """Save the collection."""
        logger.info("=== Save action triggered ===")
        try:
            log_panel = self.query_one("#log-panel", RichLog)
            log_panel.write("[#89dceb]Save action triggered[/]")
        except:
            logger.warning("Could not write to log panel")
            
        try:
            self.collection_manager.save_collection()
            self.notify("Collection saved successfully")
            logger.info("Collection saved successfully")
            try:
                log_panel = self.query_one("#log-panel", RichLog)
                log_panel.write("[#a6e3a1]Collection saved successfully[/]")
            except:
                pass
        except Exception as e:
            self.notify(f"Error saving: {e}", severity="error")
            logger.error(f"Error saving: {e}", exc_info=True)
            try:
                log_panel = self.query_one("#log-panel", RichLog)
                log_panel.write(f"[#f38ba8]Error saving: {e}[/]")
            except:
                pass
    
    def action_switch_to_welcome(self) -> None:
        """Switch to welcome screen."""
        self.app.switch_screen("welcome")
    
    def action_switch_to_packs(self) -> None:
        """Switch to packs screen."""
        self.app.switch_screen("packs")
    
    def action_switch_to_stats(self) -> None:
        """Switch to stats screen."""
        self.app.push_screen("stats")
    
    def action_toggle_log(self) -> None:
        """Toggle log panel for this screen."""
        logger.info(f"=== {self.__class__.__name__} toggle_log ===")
        self.app.log_visible = not self.app.log_visible
        self.toggle_log_panel(self.app.log_visible)
        status = "opened" if self.app.log_visible else "closed"
        self.app.notify(f"Log panel {status}")
    
    def action_quit(self) -> None:
        """Quit the app."""
        self.app.exit("quit")
    
    def action_toggle_mine(self) -> None:
        """Toggle showing only expected/different cards."""
        self.show_mine_only = not self.show_mine_only
        logger.info(f"Mine filter toggled: {self.show_mine_only}")
        self.run_worker(self.populate_card_table)
    
    def action_focus_filter(self) -> None:
        """Show and focus the filter input."""
        self.filterable_table.show_filter()
    
    async def on_filterable_data_table_filter_changed(self, message: FilterableDataTable.FilterChanged) -> None:
        """Handle filter changes from the FilterableDataTable."""
        self.filter_text = message.filter_text
        await self.populate_card_table()
    


class StatsScreen(BaseScreen):
    """Screen for viewing collection statistics."""
    
    CSS = BaseScreen.CSS + """
    .title {
        height: 1;
        text-align: center;
        background: #45475a;         /* Surface1 */
        color: #cdd6f4;              /* Text */
        content-align: center middle;
        text-style: bold;
    }
    
    .stats-summary {
        height: 3;
        background: #313244;         /* Surface0 */
        border: solid #45475a;       /* Surface1 */
        padding: 0 1;
        margin: 1;
        color: #cdd6f4;              /* Text */
    }
    
    DataTable {
        height: 1fr;
        border: solid #45475a;       /* Surface1 */
        background: #1e1e2e;         /* Base */
    }
    
    DataTable > .datatable--header {
        background: #313244;         /* Surface0 */
        color: #cba6f7;              /* Mauve */
        text-style: bold;
    }
    
    DataTable > .datatable--cursor {
        background: #cba6f7 20%;     /* Mauve with transparency */
    }
    
    DataTable > .datatable--odd-row {
        background: #181825;         /* Mantle */
    }
    
    DataTable > .datatable--even-row {
        background: #1e1e2e;         /* Base */
    }
    
    .status-bar {
        height: 1;
        background: #313244;         /* Surface0 */
        color: #a6adc8;              /* Subtext0 */
        text-align: center;
        content-align: center middle;
    }
    """
    
    BINDINGS = [
        Binding("w", "switch_to_welcome", "Welcome"),
        Binding("p", "switch_to_packs", "Packs"),
        Binding("c", "switch_to_cards", "Cards"),
        Binding("o", "toggle_log", "Log"),
        Binding("q", "quit", "Quit"),
    ]
    
    def __init__(self, collection_manager: CollectionManager, api: NetrunnerDBAPI):
        super().__init__()
        self.collection_manager = collection_manager
        self.api = api
    
    def compose(self) -> ComposeResult:
        """Create the stats screen UI."""
        yield Header(show_clock=True)
        yield Static("Collection Statistics", classes="title")
        yield Static("Loading statistics...", id="stats-summary", classes="stats-summary")
        
        table = DataTable(id="stats-table", zebra_stripes=True)
        table.add_columns("Pack", "Expected", "Actual", "Completion")
        yield table
        
        with Horizontal(classes="button-bar"):
            yield Button("⚠️ Re-initialize Collection", id="reinit-button", variant="error")
        
        yield Static(
            "nav: (w)elcome (p)acks (c)ards • q: quit",
            classes="status-bar"
        )
        yield Footer()
        yield from super().compose()  # Add log panel
    
    async def on_mount(self) -> None:
        """Initialize when the screen is mounted."""
        super().on_mount()  # Initialize log panel state
        await self.update_stats()
    
    async def update_stats(self) -> None:
        """Update collection statistics."""
        # Calculate overall stats
        all_cards = self.api.get_all_cards_list()
        
        owned_packs = len(self.collection_manager.owned_packs)
        total_packs = len(self.api.get_all_packs())
        
        expected_cards = sum(
            self.collection_manager.get_expected_card_count(card["code"]) 
            for card in all_cards
        )
        
        actual_cards = sum(
            self.collection_manager.get_actual_card_count(card["code"]) 
            for card in all_cards
        )
        
        # Update summary
        summary = self.query_one("#stats-summary", Static)
        summary.update(
            f"[bold]Packs:[/bold] {owned_packs}/{total_packs} owned  "
            f"[bold]Cards:[/bold] {actual_cards:,}/{expected_cards:,} collected"
        )
        
        # Update pack breakdown table
        table = self.query_one("#stats-table", DataTable)
        
        pack_summary = self.collection_manager.get_pack_summary(self.api)
        all_packs = self.api.get_all_packs()
        pack_names = {pack["code"]: pack["name"] for pack in all_packs}
        
        for pack_code in sorted(self.collection_manager.owned_packs):
            pack_name = pack_names.get(pack_code, "Unknown Pack")
            
            if pack_code in pack_summary:
                summary = pack_summary[pack_code]
                expected = summary["total"]
                actual = summary["owned"]
            else:
                expected = 0
                actual = 0
            
            if expected > 0:
                percentage = (actual / expected) * 100
                if percentage == 100:
                    complete_display = "[bold green]100%[/bold green]"
                elif percentage >= 75:
                    complete_display = f"[yellow]{percentage:.0f}%[/yellow]"
                else:
                    complete_display = f"{percentage:.0f}%"
            else:
                complete_display = "-"
            
            table.add_row(
                pack_name,
                str(expected),
                str(actual),
                complete_display
            )
    
    def action_switch_to_welcome(self) -> None:
        """Switch to welcome screen."""
        self.app.switch_screen("welcome")
    
    def action_switch_to_packs(self) -> None:
        """Switch to packs screen."""
        self.app.switch_screen("packs")
    
    def action_switch_to_cards(self) -> None:
        """Switch to cards screen."""
        self.app.switch_screen("cards")
    
    def action_toggle_log(self) -> None:
        """Toggle log panel for this screen."""
        logger.info(f"=== {self.__class__.__name__} toggle_log ===")
        self.app.log_visible = not self.app.log_visible
        self.toggle_log_panel(self.app.log_visible)
        status = "opened" if self.app.log_visible else "closed"
        self.app.notify(f"Log panel {status}")
    
    def action_quit(self) -> None:
        """Quit the app."""
        self.app.exit("quit")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "reinit-button":
            self.action_reinitialize()
    
    def action_reinitialize(self) -> None:
        """Re-initialize the collection with confirmation."""
        logger.info("=== Re-initialize collection requested ===")
        
        # Use a simple notification approach for confirmation
        self.notify("⚠️  Press 'y' to confirm PERMANENT DELETION of collection, or any other key to cancel", timeout=10)
        
        # We'll handle the confirmation via a key event
        self._awaiting_reinit_confirmation = True
    
    async def on_key(self, event) -> None:
        """Handle key events for re-initialization confirmation."""
        if hasattr(self, '_awaiting_reinit_confirmation') and self._awaiting_reinit_confirmation:
            self._awaiting_reinit_confirmation = False
            
            if event.key.lower() == 'y':
                try:
                    # Import here to avoid circular imports
                    from simulchip.paths import reset_simulchip_data
                    
                    # Get collection file path from the collection manager
                    collection_file = self.collection_manager.collection_file
                    
                    # Reset the data files
                    result = reset_simulchip_data(collection_path=collection_file)
                    
                    # Clear the collection manager's state completely
                    self.collection_manager.owned_packs.clear()  # Remove all owned packs
                    self.collection_manager.card_diffs.clear()  # Remove all card modifications
                    
                    # Save the now-empty collection
                    self.collection_manager.save_collection()
                    
                    # Log success
                    logger.info(f"Collection re-initialized: {len(result['removed'])} items reset")
                    
                    # Notify user and refresh stats
                    self.notify("✅ Collection successfully re-initialized", timeout=5)
                    await self.update_stats()
                    
                except Exception as e:
                    logger.error(f"Error during re-initialization: {e}", exc_info=True)
                    self.notify(f"❌ Error during re-initialization: {e}", severity="error", timeout=10)
            else:
                logger.info("Re-initialization cancelled by user")
                self.notify("Re-initialization cancelled", timeout=3)


class CollectionMainApp(App[str]):
    """Collection management app with screen-based navigation."""
    
    # Simple CSS - no log panel for now
    CSS = """
    Screen {
        background: $surface;
    }
    """
    
    BINDINGS = [
        Binding("ctrl+p", "screenshot", "Screenshot", show=False),
    ]
    
    log_visible = False  # Track log panel state across screens
    
    def __init__(self, collection_manager, api, collection_file=None):
        super().__init__()
        self.collection_manager = collection_manager
        self.api = api
        self.collection_file = collection_file
    
    def on_mount(self) -> None:
        """Set up screens when the app starts."""
        # Install screens
        self.install_screen(WelcomeScreen(), name="welcome")
        self.install_screen(PacksScreen(self.collection_manager, self.api), name="packs")
        self.install_screen(CardsScreen(self.collection_manager, self.api), name="cards")
        self.install_screen(StatsScreen(self.collection_manager, self.api), name="stats")
        
        # Start with welcome screen
        self.push_screen("welcome")
    
    def compose(self) -> ComposeResult:
        """Create app-level components - none needed since we use screens."""
        return []
    
    def action_screenshot(self) -> None:
        """Take a screenshot and save to current directory."""
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
        filename = f"simulchip_screenshot_{timestamp}.svg"
        self.save_screenshot(filename)
        self.notify(f"Screenshot saved as {filename}")
    
