"""
Root Delegation Script for Newark Regional Forecasting Notebook Builder.
Delegates to src/locations/newark/notebook_builder.py for backward compatibility.
"""

from src.locations.newark.notebook_builder import build_newark_notebook

if __name__ == "__main__":
    build_newark_notebook()
