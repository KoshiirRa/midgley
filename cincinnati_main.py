"""
Cincinnati Regional Master Execution Script (cincinnati_main.py)
Delegates directly to src/locations/cincinnati/main.py for full backward compatibility.
"""

import sys
from src.locations.cincinnati.main import run_cincinnati_pipeline

if __name__ == "__main__":
    use_api = "--use-llm-api" in sys.argv
    run_cincinnati_pipeline(use_llm_api=use_api, model_type="ridge")
