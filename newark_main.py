"""
Newark Regional Master Execution Script (newark_main.py)
Delegates directly to src/locations/newark/main.py for full backward compatibility.
"""

import sys
from src.locations.newark.main import run_newark_pipeline

if __name__ == "__main__":
    use_api = "--use-llm-api" in sys.argv
    run_newark_pipeline(use_llm_api=use_api, model_type="ridge")
