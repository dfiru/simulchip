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
simulchip collection init
```

Add cards to your collection:
```bash
# Add entire pack
simulchip collection add-pack core
simulchip collection add-pack sg

# Add individual cards
simulchip collection add-card 01001 3
```

View collection statistics:
```bash
simulchip collection stats
```

List packs:
```bash
# List all packs
simulchip collection list-packs

# List only owned packs
simulchip collection list-packs --owned
```

### Proxy Generation

Generate proxy sheets for missing cards:
```bash
simulchip proxy generate https://netrunnerdb.com/en/decklist/12345/deck-name
```

The proxy PDF will be saved to:
- Runner decks: `decks/runner/{decklist-id}/{deck-name}.pdf`
- Corp decks: `decks/corporation/{decklist-id}/{deck-name}.pdf`

Compare a decklist against your collection:
```bash
simulchip proxy compare https://netrunnerdb.com/en/decklist/12345/deck-name --detailed
```

Generate proxies for all cards (not just missing):
```bash
simulchip proxy generate https://netrunnerdb.com/en/decklist/12345/deck-name --all
```

Process multiple decklists:
```bash
# Create a file with one URL per line
echo "https://netrunnerdb.com/en/decklist/12345/deck1" > decklists.txt
echo "https://netrunnerdb.com/en/decklist/67890/deck2" >> decklists.txt

simulchip proxy batch decklists.txt
```

### Options

- `--collection` / `-c`: Specify a custom collection file (default: `~/.simulchip/collection.toml`)
- `--output` / `-o`: Specify custom output path for proxy PDFs
- `--no-images`: Generate proxies without downloading card images (faster)
- `--page-size` / `-p`: Set page size (letter, a4, legal)
- `--verbose` / `-v`: Enable verbose output

## Examples

```bash
# Initialize collection and add some packs
simulchip collection init
simulchip collection add-pack core
simulchip collection add-pack sg
simulchip collection add-pack su21

# Check what's missing from a deck
simulchip proxy compare https://netrunnerdb.com/en/decklist/12345/my-deck --detailed

# Generate proxies for missing cards
simulchip proxy generate https://netrunnerdb.com/en/decklist/12345/my-deck

# Generate proxies for all cards in a deck (useful for testing)
simulchip proxy generate https://netrunnerdb.com/en/decklist/12345/my-deck --all
```
