#!/usr/bin/env python3
"""
Irrigation Gateway Runner
Chạy gateway từ modules
"""

import sys
import os

# Add modules directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'modules'))

# Import and run main
from modules.main import main

if __name__ == "__main__":
    main()