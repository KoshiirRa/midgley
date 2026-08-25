"""
Oakland & SF Bay Area Regional Master Execution Script (oakland_main.py)
Delegates directly to src/locations/oakland/main.py for full backward compatibility.
"""

import sys
from src.locations.oakland.main import run_oakland_pipeline

if __name__ == "__main__":
    use_api = "--use-llm-api" in sys.argv
    run_oakland_pipeline(use_llm_api=use_api, model_type="ridge")
