# Simulchip Generator

[![CI](https://github.com/dfiru/simulchip/actions/workflows/ci.yml/badge.svg)](https://github.com/dfiru/simulchip/actions/workflows/ci.yml)
[![Documentation](https://github.com/dfiru/simulchip/actions/workflows/docs.yml/badge.svg)](https://dfiru.github.io/simulchip/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![linting: pylint](https://img.shields.io/badge/linting-pylint-yellowgreen)](https://github.com/pylint-dev/pylint)
[![Checked with mypy](https://img.shields.io/badge/mypy-checked-blue)](http://mypy-lang.org/)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

I just started playing Netrunner about a month ago when I received a copy of System Gateway and Elevation. I love the game and I quickly realized that if I wanted to play in person, I'd have to play Standard. And if I wanted to play Standard, I would need to proxy quite a bit of cards. 

This work is heavily inspired by some work I did for Marvel Champions to solve a similar problem. I've kept that work private over concerns about Marvel and FFG copyrights. However, with Null Signal Games supporting the game and proxies not only being legal but encouraged, I thought it was time to bring this all together here. 

The result is a clean, efficient CLI tool that does exactly what it says on the tin - no fuss, no bloat, just functional software that gets the job done. I hope you enjoy.

---

A Python CLI tool to compare NetrunnerDB decklists against your local card collection and generate print-ready PDF proxy sheets for missing cards.

## Features

- 🃏 **Smart Decklist Input**: Accept full NetrunnerDB URLs
- 📦 **Pack-Based Collection**: Manage your collection by entire packs instead of individual cards
- 🎨 **High-Quality Proxies**: Generate PDFs with actual card images from NetrunnerDB
- 📐 **Perfect Dimensions**: Cards sized exactly to Netrunner specifications (63mm x 88mm)
- ✂️ **Cut Guidelines**: Dashed lines show exactly where to cut for perfect cards
- 💾 **Smart Caching**: Downloads card data and images once, reuses for speed
- 🏷️ **Organized Output**: Files named by faction and deck for easy organization

## Installation

### Option 1: Download Executable (Recommended)
Download the latest release for your platform from the [Releases page](https://github.com/dfiru/simulchip/releases):
- **Windows**: `simulchip-windows.zip` - Extract and run `simulchip.exe`
- **macOS**: `simulchip-macos.tar.gz` - Extract, make executable (`chmod +x simulchip`), and run
- **Linux**: `simulchip-linux.tar.gz` - Extract, make executable (`chmod +x simulchip`), and run

### Option 2: Install from Source
```bash
git clone https://github.com/dfiru/simulchip.git
cd simulchip
pip install -e .
```

## Quick Start

### 1. Initialize Your Collection
```bash
# Create a new collection file
simulchip init my_collection.toml

# Add packs you own (much easier than individual cards!)
simulchip add_pack my_collection.toml sg    # System Gateway
simulchip add_pack my_collection.toml elev  # Elevation
```

### 2. Generate Proxies
```bash
# Just paste the NetrunnerDB URL!
simulchip compare "https://netrunnerdb.com/en/decklist/7a9e2d43-bd55-45d0-bd2c-99cad2d17d4c/aggravated-assault-zahya" \
  --collection my_collection.toml \
  --output .
```

### 3. Print and Cut
Open the generated PDF and print on standard letter paper. Follow the dashed cut lines for perfectly sized Netrunner cards!

## CLI Commands

### `compare` - Generate Proxy PDFs
Compare a decklist against your collection and generate proxies for missing cards.

```bash
simulchip compare <decklist_url> [OPTIONS]
```

**Examples:**
```bash
# Full URL (just copy from browser)
simulchip compare "https://netrunnerdb.com/en/decklist/12345/my-deck" --collection cards.toml --output .

# Without card images (faster)
simulchip compare "https://netrunnerdb.com/en/decklist/12345/my-deck" --collection cards.toml --output proxies.pdf --no_images

# Group by pack in PDF
simulchip compare "https://netrunnerdb.com/en/decklist/12345/my-deck" --collection cards.toml --output proxies.pdf --group_by_pack
```

**Options:**
- `--collection` / `-c`: Path to your collection file
- `--output` / `-o`: Output PDF path (or directory for auto-naming)
- `--no_images`: Generate without downloading card images (faster)
- `--group_by_pack`: Organize cards by pack in the PDF
- `--page_size`: Paper size (`letter` or `a4`, default: `letter`)

### Collection Management

The collection file is a simple TOML format - if you're comfortable editing it directly, go ahead! The CLI provides convenience functions to safely manage your collection without worrying about syntax errors or data corruption.

#### `init` - Create Collection File
```bash
simulchip init my_collection.toml
```

#### `add_pack` / `remove_pack` - Manage Packs
```bash
# Add entire pack (assumes 3 copies of each card)
simulchip add_pack my_collection.toml core

# Remove entire pack
simulchip remove_pack my_collection.toml core
```

#### `add` / `remove` - Manage Individual Cards
```bash
# Add specific cards
simulchip add my_collection.toml 01001 --count 3

# Remove specific cards
simulchip remove my_collection.toml 01001 --count 1
```

#### `mark_missing` / `found` - Track Missing Cards
Sometimes cards go missing from your collection (maybe someone played Cupellation a little too realistically at the last local?). Mark them as missing to ensure you print extras when needed:

```bash
# Mark cards as missing from your collection
# Perfect for when your friend "Cupellates" your card and takes it home
simulchip mark_missing my_collection.toml 34080 --count 1

# Mark missing cards as found (when you finally get your card back)
simulchip found my_collection.toml 34080 --count 1
```

The missing cards feature accounts for lost, damaged, or "permanently borrowed" cards by reducing your available count. When comparing decklists, you'll automatically get proxies to replace what's missing.

#### `list_packs` - Browse Available Packs
```bash
simulchip list_packs
```

#### `stats` - View Collection Statistics
```bash
simulchip stats my_collection.toml
```

### Cache Management

#### `cache` - Manage Downloaded Data
```bash
# View cache statistics
simulchip cache --stats

# Clear all cached data
simulchip cache --clear
```

## Collection File Format

Define your collection using packs (recommended) and/or individual cards:

### TOML Format
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

## Finding Pack and Card Codes

### Pack Codes
Use the `list_packs` command to see all available packs:
```bash
simulchip list_packs
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

## Output Examples

### Console Output
```
[C] Zahya Sadeghi: Versatile Smuggler
Decklist: Aggravated Assault Zahya (1st/undefeated at Denver Megacity)
ID: 7a9e2d43-bd55-45d0-bd2c-99cad2d17d4c

Total cards needed: 46
Cards owned: 15
Cards missing: 31

Missing cards by pack:
--------------------------------------------------

Midnight Sun:
  2x Cezve (33017)
  3x Steelskin Scarring (33004)
...
```

### Generated Files
When outputting to a directory, files are automatically named:
- `crim_Aggravated_Assault_Zahya.pdf`
- `hb_Glacier_Control_Deck.pdf`
- `anarch_Noise_Mill.pdf`

## PDF Features

- **Exact Card Size**: 63mm × 88mm (official Netrunner dimensions)
- **3×3 Grid Layout**: 9 cards per page, optimized for letter paper
- **Cut Guidelines**: Dashed lines show exactly where to cut
- **Real Card Images**: Downloads actual artwork from NetrunnerDB
- **Smart Fallback**: Text placeholders for cards without images
- **High Quality**: Vector graphics for clean printing

## Documentation

Full API documentation is available at [https://dfiru.github.io/simulchip/](https://dfiru.github.io/simulchip/)

## Tips

1. **Start with Packs**: Much easier than tracking individual cards
2. **Use Full URLs**: Just copy-paste from NetrunnerDB browser
3. **Directory Output**: Let the tool name files automatically
4. **Cache Management**: Clear cache if you want fresh card data
5. **Test Print**: Print one page first to verify your printer settings

## Requirements

- Python 3.10+
- Internet connection (for downloading card data/images)
- PDF viewer for reviewing proxies

## Dependencies

- `fire` - CLI framework
- `requests` - HTTP requests
- `reportlab` - PDF generation
- `Pillow` - Image processing
- `toml` - TOML file support

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines on how to contribute to this project.

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- Card data and images from [NetrunnerDB](https://netrunnerdb.com)
- Inspired by the Netrunner community's need for accessible proxy printing
- Built with love for the best card game ever made ❤️
