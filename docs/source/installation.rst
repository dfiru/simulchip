Installation
============

Requirements
------------

* Python 3.10 or higher (supports 3.10, 3.11, 3.12, 3.13)
* pip package manager

Install from PyPI
-----------------

The recommended way to install simulchip:

.. code-block:: bash

   pip install simulchip

Development Installation
------------------------

For development work, clone the repository and install in editable mode:

.. code-block:: bash

   git clone https://github.com/dfiru/simulchip.git
   cd simulchip
   pip install -e ".[dev]"

For documentation development:

.. code-block:: bash

   pip install -e ".[dev,docs]"
   pre-commit install

Verify Installation
-------------------

.. code-block:: bash

   simulchip version
