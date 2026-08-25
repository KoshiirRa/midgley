"""
Root Delegation Script for Cincinnati Regional Forecasting Notebook Builder.
Delegates to src/locations/cincinnati/notebook_builder.py for backward compatibility.
"""

from src.locations.cincinnati.notebook_builder import build_cincinnati_notebook

if __name__ == "__main__":
    build_cincinnati_notebook()
