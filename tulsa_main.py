"""
Tulsa Regional Master Execution Script (tulsa_main.py)
Delegates directly to src/locations/tulsa/main.py for full backward compatibility.
"""

import sys
from src.locations.tulsa.main import run_tulsa_pipeline

if __name__ == "__main__":
    use_api = "--use-llm-api" in sys.argv
    run_tulsa_pipeline(use_llm_api=use_api, model_type="ridge")