"""
Root Delegation Script for Oakland Regional Forecasting Notebook Builder.
Delegates to src/locations/oakland/notebook_builder.py for backward compatibility.
"""

from src.locations.oakland.notebook_builder import build_oakland_notebook

if __name__ == "__main__":
    build_oakland_notebook()
