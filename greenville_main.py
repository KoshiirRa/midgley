"""
Greenville Regional Master Execution Script (greenville_main.py)
Delegates directly to src/locations/greenville/main.py for full backward compatibility.
"""

import sys
from src.locations.greenville.main import run_greenville_pipeline

if __name__ == "__main__":
    use_api = "--use-llm-api" in sys.argv
    model_choice = "ridge"
    for arg in sys.argv:
        if arg.startswith("--model="):
            model_choice = arg.split("=")[1].lower()
            
    run_greenville_pipeline(use_llm_api=use_api, model_type=model_choice)
