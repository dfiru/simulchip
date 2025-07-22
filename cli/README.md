# Simulchip CLI

A command-line interface for managing your Netrunner card collection and generating proxy sheets.

## Installation

```bash
pip install -e .
```

## Usage

### Collection Management

Launch the interactive collection manager:
```bash
# Opens the TUI with all collection management features
simulchip collect
```

The collection manager TUI provides:
- **Pack Management**: Toggle pack ownership with filtering and search
- **Card Management**: Adjust individual card quantities
- **Statistics**: View collection completion by pack
- **Reset**: Clear and re-download collection data

Use a custom collection file:
```bash
simulchip collect --file ./my-collection.toml
```

### Proxy Generation

Generate proxy sheets for missing cards:
```bash
simulchip proxy https://netrunnerdb.com/en/decklist/12345/deck-name
```

The proxy PDF will be saved to:
- Runner decks: `decks/runner/{identity-slug}/{deck-name}.pdf`
- Corp decks: `decks/corporation/{identity-slug}/{deck-name}.pdf`

Compare a decklist against your collection (without generating PDF):
```bash
simulchip proxy https://netrunnerdb.com/en/decklist/12345/deck-name --compare-only
```

Generate proxies for all cards (not just missing):
```bash
simulchip proxy https://netrunnerdb.com/en/decklist/12345/deck-name --all
```

Select alternate printings interactively:
```bash
simulchip proxy https://netrunnerdb.com/en/decklist/12345/deck-name --alternate-prints
```


### Options

**Collection Management (`simulchip collect`):**
- `--file` / `-f`: Specify a custom collection file (default: `~/.simulchip/collection.toml`)

**Proxy Generation (`simulchip proxy`):**
- `--collection` / `-c`: Specify a custom collection file (default: `~/.simulchip/collection.toml`)
- `--output` / `-o`: Specify custom output path for proxy PDFs
- `--all` / `-a`: Generate proxies for all cards, not just missing ones
- `--no-images`: Generate proxies without downloading card images (faster)
- `--page-size` / `-p`: Set page size (letter, a4, legal) (default: letter)
- `--alternate-prints`: Interactively select alternate printings
- `--compare-only`: Only compare deck against collection, don't generate PDF
- `--detailed` / `-d`: Show detailed comparison information

## Examples

```bash
# Launch the collection manager TUI
simulchip collect

# Use a custom collection file
simulchip collect --file ./my-collection.toml

# Check what's missing from a deck
simulchip proxy https://netrunnerdb.com/en/decklist/12345/my-deck --compare-only

# Check with detailed comparison information
simulchip proxy https://netrunnerdb.com/en/decklist/12345/my-deck --compare-only --detailed

# Generate proxies for missing cards
simulchip proxy https://netrunnerdb.com/en/decklist/12345/my-deck

# Generate proxies with alternate printing selection
simulchip proxy https://netrunnerdb.com/en/decklist/12345/my-deck --alternate-prints

# Generate proxies for all cards in a deck (useful for testing)
simulchip proxy https://netrunnerdb.com/en/decklist/12345/my-deck --all

# Generate A4-sized proxies without images
simulchip proxy https://netrunnerdb.com/en/decklist/12345/my-deck --page-size a4 --no-images
```

## Interactive Features

The collection manager (`simulchip collect`) provides a rich terminal interface with:

- **Multiple Tabs**: Navigate between Packs, Cards, Stats, and Reset screens
- **Real-time filtering**: Press `/` to search for packs or cards
- **Keyboard navigation**: Arrow keys, Page Up/Down, Home/End
- **Toggle operations**: Space to toggle pack ownership, +/- for card quantities
- **Mine filter**: Press `m` in the Cards tab to show only owned cards
- **Visual feedback**: Color coding and status indicators
- **Dynamic viewport**: Automatically adjusts to terminal size

### Complete Keyboard Shortcuts

- **Tab Navigation**:
  - Tab/Shift+Tab - Cycle through tabs
  - `p` - Jump to Packs tab
  - `c` - Jump to Cards tab
  - `s` - Jump to Stats tab
  - `w` - Jump to Welcome screen
- **Filtering**: `/` - Start filter, Escape - Clear filter
- **Pack Management**: Space - Toggle pack ownership
- **Card Management**:
  - `+` or `=` - Add one card
  - `-` or `_` - Remove one card
  - `m` - Toggle "mine" filter (show only owned cards)
- **General**:
  - Ctrl+S - Save collection
  - Ctrl+C or `q` - Exit
  - `o` - Toggle debug log
  - Ctrl+P - Take screenshot
