"""
Main Orchestration Script for LLM-Augmented Unleaded Gas Price Forecasting (main.py)
Delegates directly to src/locations/national/main.py for full backward compatibility.
"""

import sys
from src.locations.national.main import run_national_pipeline as run_pipeline

if __name__ == "__main__":
    use_api = "--use-llm-api" in sys.argv
    run_pipeline(use_llm_api=use_api, model_type="ridge")
