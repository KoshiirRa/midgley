"""
Greater Chicago Regional Master Execution Script (src/locations/chicago/main.py)
Consolidated parameterized runner delegating to src/locations/runner.py (Issue #433).
"""

from __future__ import annotations
from typing import Optional, Dict, Any
from src.locations.runner import run_regional_pipeline


def run_chicago_pipeline(
    live_il_price: Optional[float] = None,
    live_in_price: Optional[float] = None,
    use_llm_api: bool = False,
    model_type: str = "ridge",
    log_wandb: bool = False
) -> Dict[str, Any]:
    """Executes the Greater Chicago Metro, IL & IN gas price prediction pipeline."""
    live_price = live_il_price if live_il_price is not None else live_in_price
    return run_regional_pipeline(
        region_id="chicago",
        live_pump_price=live_price,
        use_llm_api=use_llm_api,
        model_type=model_type,
        log_wandb=log_wandb
    )


if __name__ == "__main__":
    run_chicago_pipeline()
