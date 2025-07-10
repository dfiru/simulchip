Installation
============

Requirements
------------

* Python 3.10 or higher
* pip package manager

Install from PyPI
-----------------

.. code-block:: bash

   pip install simulchip

Install from Source
-------------------

.. code-block:: bash

   git clone https://github.com/yourusername/simulchip.git
   cd simulchip
   pip install -e .

Development Installation
------------------------

For development with all tools:

.. code-block:: bash

   git clone https://github.com/yourusername/simulchip.git
   cd simulchip
   pip install -e ".[dev,docs]"
   pre-commit install

Verify Installation
-------------------

.. code-block:: bash

   simulchip version
