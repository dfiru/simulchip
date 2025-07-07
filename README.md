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

I just started playing Netrunner about a month ago when I received a copy of System Gateway and Elevation. I love the game and I quickly realized that if I wanted to play in person, I'd have to play Standard. And if I wanted to play Standard, I would need to proxy quite a bit of cards.

This work is heavily inspired by some work I did for Marvel Champions to solve a similar problem. I've kept that work private over concerns about Marvel and FFG copyrights. However, with Null Signal Games supporting the game and proxies not only being legal but encouraged, I thought it was time to bring this all together here.

The result is a clean, efficient Python library that does exactly what it says on the tin - no fuss, no bloat, just functional software that gets the job done. I hope you enjoy.

---

## Features

- 🃏 **Smart Decklist Input**: Accept full NetrunnerDB URLs or deck IDs
- 📦 **Pack-Based Collection**: Manage your collection by entire packs instead of individual cards
- 🎨 **High-Quality Proxies**: Generate PDFs with actual card images from NetrunnerDB
- 📐 **Perfect Dimensions**: Cards sized exactly to Netrunner specifications (63mm x 88mm)
- ✂️ **Cut Guidelines**: Dashed lines show exactly where to cut for perfect cards
- 💾 **Smart Caching**: Downloads card data and images once, reuses for speed
- 🏷️ **Organized Output**: Files named by faction and deck for easy organization
- 🐍 **Pure Python**: Simple library you can integrate into your own tools

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

### 1. Using the CLI Tool
```bash
# Initialize a new collection
simulchip collection init

# Add packs to your collection
simulchip collection add-pack sg core elev

# Generate proxies for a deck
simulchip proxy generate https://netrunnerdb.com/en/decklist/7a9e2d43-bd55-45d0-bd2c-99cad2d17d4c

# Compare multiple decks
simulchip proxy compare deck1.txt deck2.txt deck3.txt
```

### 2. Run the Example Script
```bash
python example.py
```

This will demonstrate all the main library features and create example files.

### 3. Basic Library Usage

```python
from pathlib import Path
from simulchip.api.netrunnerdb import NetrunnerDBAPI
from simulchip.collection.manager import CollectionManager
from simulchip.comparison import DecklistComparer
from simulchip.pdf.generator import ProxyPDFGenerator

# Initialize components
api = NetrunnerDBAPI()
collection_path = Path("my_collection.toml")
collection = CollectionManager(collection_path, api)

# Add packs to your collection
collection.add_pack("sg")    # System Gateway
collection.add_pack("core")  # Core Set
collection.save_collection()

# Compare a decklist
comparer = DecklistComparer(api, collection)
result = comparer.compare_decklist("7a9e2d43-bd55-45d0-bd2c-99cad2d17d4c")

print(f"Missing {result.stats.missing_cards} cards from {result.decklist_name}")

# Generate PDF for missing cards
if result.stats.missing_cards > 0:
    pdf_gen = ProxyPDFGenerator(api)
    proxy_cards = comparer.get_proxy_cards(result)
    pdf_gen.generate_proxy_pdf(proxy_cards, Path("proxies.pdf"))
```

## Command-Line Interface

The `simulchip` CLI provides a convenient way to manage your collection and generate proxy sheets without writing code.

### Collection Management

```bash
# Initialize a new collection (creates ~/.simulchip/collection.toml)
simulchip collection init

# Add entire packs to your collection
simulchip collection add-pack sg core elev ms

# Remove packs from your collection
simulchip collection remove-pack sg

# Add individual cards
simulchip collection add-card 30010 --quantity 3

# Remove individual cards
simulchip collection remove-card 30010 --quantity 1

# Mark cards as missing/lost
simulchip collection mark-missing 30010 --quantity 1

# Show collection summary
simulchip collection show

# Use a custom collection file
simulchip collection init --path ./my-collection.toml
simulchip collection add-pack sg --path ./my-collection.toml
```

### Proxy Generation

```bash
# Generate proxies for a single deck
simulchip proxy generate https://netrunnerdb.com/en/decklist/7a9e2d43-bd55-45d0-bd2c-99cad2d17d4c

# Generate proxies using deck ID only
simulchip proxy generate 7a9e2d43-bd55-45d0-bd2c-99cad2d17d4c

# Compare multiple decks and generate reports
simulchip proxy compare deck1.txt deck2.txt deck3.txt

# Batch generate proxies for multiple decks
simulchip proxy batch decklist-urls.txt

# Custom output directory
simulchip proxy generate DECK_ID --output-dir ./my-proxies

# Use custom collection file
simulchip proxy generate DECK_ID --collection ./my-collection.toml
```

### Proxy Output Structure

By default, proxy PDFs are saved to `decks/` with the following structure:
```
decks/
├── corporation/
│   └── weyland-consortium/
│       └── my-deck-name.pdf
└── runner/
    └── anarch/
        └── my-runner-deck.pdf
```

### CLI Configuration

The CLI uses `~/.simulchip/collection.toml` as the default collection file. You can override this with the `--collection` flag on most commands.

## Core Library Components

### NetrunnerDBAPI
Handles all communication with the NetrunnerDB API.

```python
from simulchip.api.netrunnerdb import NetrunnerDBAPI

api = NetrunnerDBAPI()

# Get all cards
cards = api.get_all_cards()

# Get all packs
packs = api.get_all_packs()

# Get specific pack
pack = api.get_pack_by_code("sg")

# Get specific card
card = api.get_card_by_code("30010")

# Get decklist
decklist = api.get_decklist("7a9e2d43-bd55-45d0-bd2c-99cad2d17d4c")
```

### CollectionManager
Manages your local card collection stored in TOML files.

```python
from simulchip.collection.manager import CollectionManager
from pathlib import Path

collection = CollectionManager(Path("collection.toml"), api)

# Add entire packs
collection.add_pack("sg")
collection.add_pack("core")

# Add individual cards
collection.add_card("30010", 3)  # 3 copies of Zahya

# Mark cards as missing/lost
collection.add_missing_card("30010", 1)  # Lost 1 copy

# Remove cards
collection.remove_card("30010", 1)

# Get card counts
count = collection.get_card_count("30010")  # Available copies

# Save changes
collection.save_collection()
```

### DecklistComparer
Compares NetrunnerDB decklists against your collection.

```python
from simulchip.comparison import DecklistComparer

comparer = DecklistComparer(api, collection)

# Compare by decklist ID
result = comparer.compare_decklist("7a9e2d43-bd55-45d0-bd2c-99cad2d17d4c")

# Access comparison results
print(f"Deck: {result.decklist_name}")
print(f"Identity: {result.identity_name}")
print(f"Total cards: {result.stats.total_cards}")
print(f"Owned: {result.stats.owned_cards}")
print(f"Missing: {result.stats.missing_cards}")

# Get formatted report
report = comparer.format_comparison_report(result)
print(report)

# Get proxy cards for PDF generation
proxy_cards = comparer.get_proxy_cards(result)
```

### ProxyPDFGenerator
Generates print-ready PDFs with card images.

```python
from simulchip.pdf.generator import ProxyPDFGenerator

pdf_gen = ProxyPDFGenerator(api, page_size="letter")  # or "a4"

# Generate PDF
pdf_gen.generate_proxy_pdf(
    proxy_cards,
    Path("output.pdf"),
    download_images=True,    # Include card images
    group_by_pack=True      # Group cards by pack
)
```

## Collection File Format

Your collection is stored in a simple TOML file:

```toml
# Own entire packs (3 copies of each card)
packs = [
  "core",   # Core Set
  "sg",     # System Gateway
  "elev",   # Elevation
  "ms",     # Midnight Sun
]

# Override specific cards (optional)
[cards]
"01016" = 2  # Only have 2x Account Siphon
"22001" = 1  # Single promo card

# Track missing/lost cards (optional)
[missing]
"34080" = 1  # Lost to Cupellation!
```

## Building Your Own Tools

The library is designed to be flexible. Here are some ideas for custom tools you could build:

### Automatic Collection Sync
```python
# Sync your collection with a CSV export from another tool
import csv
from simulchip.collection.manager import CollectionManager

def sync_from_csv(csv_path, collection_path):
    collection = CollectionManager(collection_path, api)

    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            collection.add_card(row['card_code'], int(row['quantity']))

    collection.save_collection()
```

### Batch Proxy Generation
```python
# Generate proxies for multiple decklists
def generate_proxies_for_decklists(decklist_urls, collection_path):
    collection = CollectionManager(collection_path, api)
    comparer = DecklistComparer(api, collection)
    pdf_gen = ProxyPDFGenerator(api)

    for url in decklist_urls:
        deck_id = extract_decklist_id(url)
        result = comparer.compare_decklist(deck_id)

        if result.stats.missing_cards > 0:
            proxy_cards = comparer.get_proxy_cards(result)
            output_path = Path(f"{result.identity_faction}_{result.decklist_name}.pdf")
            pdf_gen.generate_proxy_pdf(proxy_cards, output_path)
```

### Custom Reports
```python
# Generate a collection completion report
def collection_completion_report(collection_path):
    collection = CollectionManager(collection_path, api)
    all_packs = api.get_all_packs()

    for pack in all_packs:
        pack_cards = api.get_cards_by_pack(pack['code'])
        owned_count = sum(1 for card in pack_cards
                         if collection.get_card_count(card['code']) > 0)
        completion = owned_count / len(pack_cards) * 100
        print(f"{pack['name']}: {completion:.1f}% complete")
```

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

## Dependencies

- `requests` - HTTP requests to NetrunnerDB API
- `reportlab` - PDF generation
- `Pillow` - Image processing
- `toml` - TOML file support

## Documentation

Full API documentation is available at [https://dfiru.github.io/simulchip/](https://dfiru.github.io/simulchip/)

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines on how to contribute to this project.

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- Card data and images from [NetrunnerDB](https://netrunnerdb.com)
- Inspired by the Netrunner community's need for accessible proxy printing
- Built with love for the best card game ever made ❤️
