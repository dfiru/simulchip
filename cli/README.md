# Simulchip CLI

A command-line interface for managing your Netrunner card collection and generating proxy sheets.

## Installation

```bash
pip install -e .
```

## Usage

### Collection Management

Initialize a new collection:
```bash
simulchip collect init
```

Manage packs interactively:
```bash
# Interactive pack management with filtering and navigation
simulchip collect packs
```

Manage cards interactively:
```bash
# Interactive card management with filtering and navigation
simulchip collect cards
```

View collection statistics:
```bash
simulchip collect stats
```

Reset collection data:
```bash
# Reset and re-download pack/card information
simulchip collect reset
```

### Proxy Generation

Generate proxy sheets for missing cards:
```bash
simulchip proxy generate https://netrunnerdb.com/en/decklist/12345/deck-name
```

The proxy PDF will be saved to:
- Runner decks: `decks/runner/{identity-slug}/{deck-name}.pdf`
- Corp decks: `decks/corporation/{identity-slug}/{deck-name}.pdf`

Compare a decklist against your collection:
```bash
simulchip proxy compare https://netrunnerdb.com/en/decklist/12345/deck-name
```

Generate proxies for all cards (not just missing):
```bash
simulchip proxy generate https://netrunnerdb.com/en/decklist/12345/deck-name --all
```

Select alternate printings interactively:
```bash
simulchip proxy generate https://netrunnerdb.com/en/decklist/12345/deck-name --alternate-prints
```


### Options

- `--collection` / `-c`: Specify a custom collection file (default: `~/.simulchip/collection.toml`)
- `--output` / `-o`: Specify custom output path for proxy PDFs
- `--no-images`: Generate proxies without downloading card images (faster)
- `--page-size` / `-p`: Set page size (letter, a4, legal)
- `--verbose` / `-v`: Enable verbose output

## Examples

```bash
# Initialize collection
simulchip collect init

# Interactively manage packs
simulchip collect packs

# Interactively manage cards
simulchip collect cards

# Check what's missing from a deck
simulchip proxy compare https://netrunnerdb.com/en/decklist/12345/my-deck

# Generate proxies for missing cards
simulchip proxy generate https://netrunnerdb.com/en/decklist/12345/my-deck

# Generate proxies with alternate printing selection
simulchip proxy generate https://netrunnerdb.com/en/decklist/12345/my-deck --alternate-prints

# Generate proxies for all cards in a deck (useful for testing)
simulchip proxy generate https://netrunnerdb.com/en/decklist/12345/my-deck --all
```

## Interactive Features

The collection management commands (`collect packs` and `collect cards`) provide rich terminal interfaces with:

- **Real-time filtering**: Type to search for packs or cards
- **Keyboard navigation**: Arrow keys, Page Up/Down, Home/End
- **Toggle operations**: Space to toggle pack ownership, +/- for card quantities
- **Visual feedback**: Color coding and status indicators
- **Dynamic viewport**: Automatically adjusts to terminal size
