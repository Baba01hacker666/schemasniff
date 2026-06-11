#!/usr/bin/env python3
import sys
import os

# Add the current directory to sys.path so the package can be imported directly
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from schemasniff.main import main

if __name__ == '__main__':
    main()
