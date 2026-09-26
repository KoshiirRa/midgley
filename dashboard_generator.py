"""
Root Forwarding Shim (dashboard_generator.py)
Directs execution to src/dashboard_generator.py (Issue #441).
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from src.dashboard_generator import *  # noqa: F401, F403

if __name__ == "__main__":
    from src.dashboard_generator import generate_public_dashboard
    generate_public_dashboard()
