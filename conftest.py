# conftest.py  –  SST3 Python Edition tests
# Version 0.1.0
#
# Adds the parent directory to sys.path so tests can import the game modules
# without installation.  pytest picks this up automatically.

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
