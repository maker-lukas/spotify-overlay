#!/usr/bin/env python3
"""Dev launcher - runs the overlay directly without installing."""
import sys
import os

# Allow importing spotify_overlay as a package when running from source
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from spotify_overlay.__main__ import main

if __name__ == "__main__":
    main()
