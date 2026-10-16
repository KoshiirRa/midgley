"""
New York Regional Master Execution Script (src/locations/new_york/main.py)
Consolidated parameterized runner delegating to src/locations/runner.py (Issue #433, Issue #635).
"""

from __future__ import annotations
from typing import Optional, Dict, Any
from src.locations.runner import run_regional_pipeline


def run_new_york_pipeline(
    live_pump_price: Optional[float] = None,
    use_llm_api: bool = False,
    model_type: str = "ridge",
    log_wandb: bool = False
) -> Dict[str, Any]:
    """Executes the New York Harbor & New York State Regional Hub gas price prediction pipeline."""
    return run_regional_pipeline(
        region_id="new_york",
        live_pump_price=live_pump_price,
        use_llm_api=use_llm_api,
        model_type=model_type,
        log_wandb=log_wandb
    )


if __name__ == "__main__":
    run_new_york_pipeline()
