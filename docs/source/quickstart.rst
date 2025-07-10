Quick Start Guide
=================

This guide will help you get started with the Simulchip library.

Installation
------------

Install from source:

.. code-block:: bash

   git clone https://github.com/dfiru/simulchip.git
   cd simulchip
   pip install -e .

Or install as a dependency:

.. code-block:: bash

   pip install git+https://github.com/dfiru/simulchip.git

Using the CLI
--------------

The quickest way to get started is with the CLI:

.. code-block:: bash

   # Initialize a new collection
   simulchip collect init

   # Interactive collection management
   simulchip collect manage

   # Generate proxies for a deck
   simulchip proxy generate https://netrunnerdb.com/en/decklist/7a9e2d43-bd55-45d0-bd2c-99cad2d17d4c

Basic Library Usage
-------------------

Initialize Components
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from pathlib import Path
   from simulchip.api.netrunnerdb import NetrunnerDBAPI
   from simulchip.collection.operations import get_or_create_manager
   from simulchip.comparison import DecklistComparer
   from simulchip.pdf.generator import ProxyPDFGenerator

   # Initialize API and collection
   api = NetrunnerDBAPI()
   collection_path = Path("my_collection.toml")
   collection = get_or_create_manager(collection_path, api, all_cards=False)

Managing Your Collection
~~~~~~~~~~~~~~~~~~~~~~~~

Add entire packs to your collection:

.. code-block:: python

   # Add packs
   collection.add_pack("sg")    # System Gateway
   collection.add_pack("core")  # Core Set

   # Modify individual card quantities
   collection.modify_card_quantity("30010", 1)   # Add 1 copy
   collection.modify_card_quantity("30010", -1)  # Remove 1 copy

   # Set absolute quantities
   collection.set_card_quantity("30010", 2)  # Set to exactly 2 copies

   # Save changes
   collection.save_collection()

Comparing Decklists
~~~~~~~~~~~~~~~~~~~

Compare a NetrunnerDB decklist against your collection:

.. code-block:: python

   comparer = DecklistComparer(api, collection)
   result = comparer.compare_decklist("7a9e2d43-bd55-45d0-bd2c-99cad2d17d4c")

   print(f"Missing {result.stats.missing_cards} cards from {result.decklist_name}")
   print(f"Identity: {result.identity.title}")
   print(f"Completion: {result.stats.completion_percentage:.1f}%")

Generating PDF Proxies
~~~~~~~~~~~~~~~~~~~~~~

Generate proxy PDFs for missing cards:

.. code-block:: python

   if result.stats.missing_cards > 0:
       pdf_gen = ProxyPDFGenerator(api)
       proxy_cards = comparer.get_proxy_cards_for_generation(result, all_cards=False)
       pdf_gen.generate_proxy_pdf(
           proxy_cards,
           Path("proxies.pdf"),
           download_images=True,
           group_by_pack=True,
           interactive_printing_selection=False
       )

CLI Reference
-------------

Collection Management Commands:

.. code-block:: bash

   # Initialize collection
   simulchip collect init

   # Interactive management
   simulchip collect manage
   simulchip collect packs
   simulchip collect cards

   # Reset collection data
   simulchip collect reset

Proxy Generation Commands:

.. code-block:: bash

   # Generate proxies
   simulchip proxy generate URL
   simulchip proxy generate URL --alternate-prints
   simulchip proxy generate URL --all --no-images

   # Compare decks
   simulchip proxy compare URL

   # Batch processing
   simulchip proxy batch urls.txt

New Library Features
--------------------

The library now includes several new modules:

- **batch** - Batch processing utilities
- **cli_utils** - CLI business logic
- **display** - Display and formatting utilities
- **filters** - Filtering and search functions
- **interactive** - Interactive interface management
- **models** - Data models and wrappers
- **paths** - Path management utilities
- **platform** - Platform-specific utilities
- **collection.operations** - Collection operation helpers

Building Custom Tools
---------------------

Example using new utilities:

.. code-block:: python

   from simulchip.batch import process_decklist_batch
   from simulchip.filters import filter_packs_raw
   from simulchip.display import get_completion_color

   # Process multiple decks at once
   result = process_decklist_batch(
       decklist_file=Path("urls.txt"),
       generate_func=my_generate_function,
       progress_callback=my_progress_callback
   )

   # Filter packs with search
   filtered_packs = filter_packs_raw(all_packs, "core")

   # Get color coding for completion percentages
   color = get_completion_color(75.0)  # Returns "yellow"

See the API reference for complete documentation of all modules and functions.
