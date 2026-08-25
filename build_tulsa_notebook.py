"""
Root Delegation Script for Tulsa Regional Forecasting Notebook Builder.
Delegates to src/locations/tulsa/notebook_builder.py for backward compatibility.
"""

from src.locations.tulsa.notebook_builder import build_tulsa_notebook

if __name__ == "__main__":
    build_tulsa_notebook()
