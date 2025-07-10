# Simulchip - Netrunner Proxy Library

[![CI](https://github.com/dfiru/simulchip/actions/workflows/ci.yml/badge.svg)](https://github.com/dfiru/simulchip/actions/workflows/ci.yml)
[![Documentation](https://github.com/dfiru/simulchip/actions/workflows/docs.yml/badge.svg)](https://dfiru.github.io/simulchip/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![linting: pylint](https://img.shields.io/badge/linting-pylint-yellowgreen)](https://github.com/pylint-dev/pylint)
[![Checked with mypy](https://img.shields.io/badge/mypy-checked-blue)](http://mypy-lang.org/)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

A Python library for comparing NetrunnerDB decklists against your local card collection and generating print-ready PDF proxy sheets for missing cards.

I just started playing Netrunner about a month ago when I purchased a copy of System Gateway and Elevation. I love the game and I quickly realized that if I wanted to play in paper, I'd probably have to play Standard. And if I wanted to play Standard, I would need to proxy quite a bit of cards.  Enter Simulchip: an easy way to manage your collection and proxy missing cards.

This work is heavily inspired by some work I did for Marvel Champions to solve a similar problem. I've kept that work private over concerns about Marvel and FFG copyrights. However, with Null Signal Games supporting the game and proxies not only being legal but encouraged, I thought it was time to bring this all together here.

The result is a clean, efficient Python library and CLI tool that does exactly what it says help you print the proxies that you need.

---

## Features

- 🃏 **Smart Decklist Input**: Accept full NetrunnerDB URLs or deck IDs
- 📦 **Interactive Collection Management**: Rich terminal interface for managing packs and cards
- 🎨 **High-Quality Proxies**: Generate PDFs with actual card images from NetrunnerDB
- 🖼️ **Alternate Printing Selection**: Choose between different card printings interactively
- 📐 **Perfect Dimensions**: Cards sized exactly to Netrunner specifications (63mm x 88mm)
- ✂️ **Cut Guidelines**: Dashed lines show exactly where to cut for perfect cards
- 💾 **Smart Caching**: Downloads card data and images once, reuses for speed and to be as nice as possible to NRDB apis
- 🏷️ **Identity-Based Organization**: Files organized by identity names for easy browsing
- 🔍 **Advanced Filtering**: Search and filter collections with real-time updates
- 📊 **Batch Processing**: Generate proxies for multiple decks at once
- 🐍 **Pure Python**: Clean library architecture with CLI as a lightweight interface

## Installation

### Option 1: Install from Source
```bash
git clone https://github.com/dfiru/simulchip.git
cd simulchip
pip install -e .
```

### Option 2: Use as Library Dependency
```bash
pip install git+https://github.com/dfiru/simulchip.git
```

After installation, you'll have both the Python library and the `simulchip` command-line tool available.

## Quick Start

### 1. Initialize Your Collection
```bash
# Initialize a new collection
simulchip collect init

# Interactively manage packs in your collection
simulchip collect packs

# Interactively manage individual cards
simulchip collect cards
```

### 2. Generate Proxy Sheets
```bash
# Generate proxies for a deck
simulchip proxy https://netrunnerdb.com/en/decklist/7a9e2d43-bd55-45d0-bd2c-99cad2d17d4c

# Compare a deck against your collection (no PDF generation)
simulchip proxy https://netrunnerdb.com/en/decklist/7a9e2d43-bd55-45d0-bd2c-99cad2d17d4c --compare-only

```

### 3. Interactive Management

The collection commands provide rich terminal interfaces with filtering, navigation, and real-time updates:

```bash
# Manage packs with filtering and search
simulchip collect packs

# Manage individual cards with detailed controls
simulchip collect cards

# View collection statistics
simulchip collect stats
```

## Command-Line Interface

The `simulchip` CLI is the primary interface for managing your collection and generating proxy sheets.

### Collection Management

```bash
# Initialize a new collection (creates ~/.simulchip/collection.toml)
simulchip collect init

# Interactive pack management with filtering and navigation
simulchip collect packs

# Interactive card management with filtering and navigation
simulchip collect cards

# Show collection statistics
simulchip collect stats

# Reset collection data and re-download pack/card information
simulchip collect reset

# Use a custom collection file
simulchip collect init --collection ./my-collection.toml
simulchip collect packs --collection ./my-collection.toml
```

### Proxy Generation

```bash
# Generate proxies for a single deck
simulchip proxy https://netrunnerdb.com/en/decklist/7a9e2d43-bd55-45d0-bd2c-99cad2d17d4c

# Generate proxies using deck ID only
simulchip proxy 7a9e2d43-bd55-45d0-bd2c-99cad2d17d4c

# Compare a deck against your collection (no PDF generation)
simulchip proxy DECK_ID --compare-only

# Generate proxies for all cards (not just missing ones)
simulchip proxy DECK_ID --all

# Skip downloading card images for faster generation
simulchip proxy DECK_ID --no-images

# Interactive alternate printing selection
simulchip proxy DECK_ID --alternate-prints

# Custom output path
simulchip proxy DECK_ID --output ./my-proxies/deck.pdf

# Use custom collection file
simulchip proxy DECK_ID --collection ./my-collection.toml
```

### Proxy Output Structure

By default, proxy PDFs are saved to `decks/` with the following structure based on identity names:
```
decks/
├── corporation/
│   └── weyland-consortium-building-a-better-world/
│       └── my-deck-name.pdf
└── runner/
    └── zahya-sadeghi-versatile-smuggler/
        └── my-runner-deck.pdf
```

This creates meaningful folder names based on the actual identity cards rather than NetrunnerDB UUIDs.

### CLI Configuration

The CLI uses `~/.simulchip/collection.toml` as the default collection file. You can override this with the `--collection` flag on most commands.

#### Interactive Features
- **Rich Terminal Interface**: Color-coded tables with dynamic viewport sizing
- **Real-time Filtering**: Type to filter packs/cards with instant updates
- **Keyboard Navigation**: Arrow keys, page up/down, vim-style shortcuts
- **Batch Operations**: Toggle multiple packs/cards at once
- **Platform Support**: Works on Windows, macOS, and Linux

## Python Library

Simulchip also provides a comprehensive Python library for building custom tools and integrations.

### Quick Library Example
```python
from simulchip.api.netrunnerdb import NetrunnerDBAPI
from simulchip.collection.operations import get_or_create_manager
from simulchip.comparison import DecklistComparer
from simulchip.pdf.generator import ProxyPDFGenerator
from pathlib import Path

# Initialize components
api = NetrunnerDBAPI()
collection = get_or_create_manager(Path("collection.toml"), api)

# Compare a deck
comparer = DecklistComparer(api, collection)
result = comparer.compare_decklist("7a9e2d43-bd55-45d0-bd2c-99cad2d17d4c")

# Generate proxies
if result.stats.missing_cards > 0:
    pdf_gen = ProxyPDFGenerator(api)
    proxy_cards = comparer.get_proxy_cards_for_generation(result, all_cards=False)
    pdf_gen.generate_proxy_pdf(proxy_cards, Path("proxies.pdf"))
```

### Library Documentation
For detailed library documentation, API reference, and advanced usage:

📚 **[Full API Documentation](https://dfiru.github.io/simulchip/)**

The library includes modules for:
- **API Integration** (`simulchip.api`) - NetrunnerDB communication
- **Collection Management** (`simulchip.collection`) - Local collection handling
- **Deck Comparison** (`simulchip.comparison`) - Deck analysis and comparison
- **PDF Generation** (`simulchip.pdf`) - Proxy sheet creation
- **Utilities** (`simulchip.filters`, `simulchip.display`, etc.) - Helper functions

## Collection File Format

Your collection is stored in a simple TOML file with a new simplified structure:

```toml
# Own entire packs (3 copies of each card)
packs = [
  "core",   # Core Set
  "sg",     # System Gateway
  "elev",   # Elevation
  "ms",     # Midnight Sun
]

# Card differences from pack defaults (optional)
[card_diffs]
"01016" = -1  # Missing 1 copy of Account Siphon (have 2 instead of 3)
"22001" = 1   # Extra promo card (have 1 instead of 0)
"34080" = -3  # Lost all copies to Cupellation!
```

The new format uses card differences (deltas) instead of absolute quantities, making it easier to track changes from the standard 3-per-pack default.

## Architecture

Simulchip follows a clean separation between the library and CLI:

- **CLI** (`cli/`) - Lightweight terminal interface with interactive features
- **Library** (`simulchip/`) - Core business logic and utilities

This design ensures the library can be used in any Python application while the CLI provides an excellent user experience for common tasks.

## Finding Pack and Card Codes

### Pack Codes
```python
# List all available packs
api = NetrunnerDBAPI()
packs = api.get_all_packs()
for pack in sorted(packs, key=lambda p: p.get("date_release", ""), reverse=True):
    print(f"{pack['code']}: {pack['name']}")
```

Common pack codes:
- `core` - Core Set
- `sg` - System Gateway
- `elev` - Elevation
- `ms` - Midnight Sun
- `su21` - System Update 2021

### Card Codes
Card codes follow the format: `PPNNN` where:
- `PP` = Pack number (01 = Core Set, 30 = System Gateway, etc.)
- `NNN` = Card number within pack

Examples: `01001` (Noise), `30010` (Zahya), `33004` (Steelskin Scarring)

## PDF Features

- **Exact Card Size**: 63mm × 88mm (official Netrunner dimensions)
- **3×3 Grid Layout**: 9 cards per page, optimized for letter paper
- **Cut Guidelines**: Dashed lines show exactly where to cut
- **Real Card Images**: Downloads actual artwork from NetrunnerDB
- **Smart Fallback**: Text placeholders for cards without images
- **High Quality**: Vector graphics for clean printing

## Development

### Dependencies
- `requests` - HTTP requests to NetrunnerDB API
- `reportlab` - PDF generation
- `Pillow` - Image processing
- `toml` - TOML file support
- `typer` - CLI framework
- `rich` - Terminal UI

### Documentation
- **API Documentation**: [https://dfiru.github.io/simulchip/](https://dfiru.github.io/simulchip/)
- **Contributing Guide**: [CONTRIBUTING.md](CONTRIBUTING.md)
- **Code of Conduct**: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines on how to contribute to this project.

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- Card data and images from [NetrunnerDB](https://netrunnerdb.com)
- Inspired by the Netrunner community's need for accessible proxy printing
- Built with love for the best card game ever made ❤️
