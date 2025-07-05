#!/usr/bin/env python3
"""
Standalone entry point for PyInstaller builds.
This avoids relative import issues by providing a clean entry point.
"""

import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and run the main function
from simulchip.cli.main import main

if __name__ == '__main__':
    main()