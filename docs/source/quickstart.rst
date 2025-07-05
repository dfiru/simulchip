Quick Start Guide
=================

This guide will help you get started with Simulchip.

Initialize Your Collection
--------------------------

First, create a collection file to track your owned cards:

.. code-block:: bash

   simulchip init

This creates a ``collection.toml`` file in your current directory.

Managing Your Collection
------------------------

Add Entire Packs
~~~~~~~~~~~~~~~~

Add all cards from a pack to your collection:

.. code-block:: bash

   simulchip add-pack gateway
   simulchip add-pack system-update-2021

Add Individual Cards
~~~~~~~~~~~~~~~~~~~~

Add specific quantities of individual cards:

.. code-block:: bash

   simulchip add-card "hedge-fund:3"
   simulchip add-card "sure-gamble:2"

View Collection Statistics
~~~~~~~~~~~~~~~~~~~~~~~~~~

See what's in your collection:

.. code-block:: bash

   simulchip stats

List Available Packs
~~~~~~~~~~~~~~~~~~~~

View all available packs:

.. code-block:: bash

   simulchip list-packs

Comparing Decklists
-------------------

Compare a NetrunnerDB decklist against your collection:

.. code-block:: bash

   simulchip compare https://netrunnerdb.com/en/decklist/12345

Generate PDF proxies for missing cards:

.. code-block:: bash

   simulchip compare https://netrunnerdb.com/en/decklist/12345 -o missing_cards.pdf

Managing the Cache
------------------

View cache statistics:

.. code-block:: bash

   simulchip cache stats

Clear the cache if needed:

.. code-block:: bash

   simulchip cache clear