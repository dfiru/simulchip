Simulchip Documentation
========================

Welcome to Simulchip's documentation! This tool helps you compare NetrunnerDB decklists against your local card collection and generate PDF proxies for missing cards.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   quickstart
   api/index
   contributing

Features
--------

* 🎯 **Smart Decklist Input**: Accept full NetrunnerDB URLs
* 📊 **Collection Tracking**: Track owned cards by individual prints or entire packs
* 🔍 **Intelligent Comparison**: Identify missing cards from any decklist
* 🖨️ **High-Quality Proxies**: Generate print-ready PDFs with proper formatting
* 🚀 **Fast & Efficient**: Smart caching system for images and API data
* 🎨 **Format Support**: TOML configuration for easy management

Quick Example
-------------

.. code-block:: bash

   # Initialize your collection
   simulchip collect init

   # Manage packs and cards interactively
   simulchip collect packs
   simulchip collect cards

   # Compare against a decklist and generate proxies
   simulchip proxy compare https://netrunnerdb.com/en/decklist/12345
   simulchip proxy generate https://netrunnerdb.com/en/decklist/12345

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
