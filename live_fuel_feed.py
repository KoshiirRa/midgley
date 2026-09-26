"""
Root Forwarding Shim (live_fuel_feed.py)
Directs execution to src/live_fuel_feed.py (Issue #441).
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from src.live_fuel_feed import *  # noqa: F401, F403
