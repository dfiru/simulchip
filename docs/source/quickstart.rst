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

Running the Example
-------------------

The quickest way to see Simulchip in action is to run the example script:

.. code-block:: bash

   python example.py

This will demonstrate all the main library features and create example files.

Basic Library Usage
-------------------

Initialize Components
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from pathlib import Path
   from simulchip.api.netrunnerdb import NetrunnerDBAPI
   from simulchip.collection.manager import CollectionManager
   from simulchip.comparison import DecklistComparer
   from simulchip.pdf.generator import ProxyPDFGenerator

   # Initialize API and collection
   api = NetrunnerDBAPI()
   collection_path = Path("my_collection.toml")
   collection = CollectionManager(collection_path, api)

Managing Your Collection
~~~~~~~~~~~~~~~~~~~~~~~~

Add entire packs to your collection:

.. code-block:: python

   # Add packs
   collection.add_pack("sg")    # System Gateway
   collection.add_pack("core")  # Core Set

   # Add individual cards
   collection.add_card("30010", 3)  # 3 copies of Zahya

   # Mark cards as missing
   collection.add_missing_card("30010", 1)  # Lost 1 copy

   # Save changes
   collection.save_collection()

Comparing Decklists
~~~~~~~~~~~~~~~~~~~

Compare a NetrunnerDB decklist against your collection:

.. code-block:: python

   comparer = DecklistComparer(api, collection)
   result = comparer.compare_decklist("7a9e2d43-bd55-45d0-bd2c-99cad2d17d4c")

   print(f"Missing {result.stats.missing_cards} cards from {result.decklist_name}")

Generating PDF Proxies
~~~~~~~~~~~~~~~~~~~~~~

Generate proxy PDFs for missing cards:

.. code-block:: python

   if result.stats.missing_cards > 0:
       pdf_gen = ProxyPDFGenerator(api)
       proxy_cards = comparer.get_proxy_cards(result)
       pdf_gen.generate_proxy_pdf(proxy_cards, Path("proxies.pdf"))

Building Custom Tools
---------------------

The library is designed to be flexible. You can build your own tools for:

- Batch processing multiple decklists
- Custom collection management workflows
- Integration with other Netrunner tools
- Web interfaces for proxy generation
- Automated collection syncing

See the main README for detailed examples of building custom tools.
