"""
Root Delegation Script for National Wholesale Forecasting Notebook Builder.
Delegates to src/locations/national/notebook_builder.py for backward compatibility.
"""

from src.locations.national.notebook_builder import build_national_notebook

if __name__ == "__main__":
    build_national_notebook()
