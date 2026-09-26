"""
Oakland Regional Master Execution Script (src/locations/oakland/main.py)
Consolidated parameterized runner delegating to src/locations/runner.py (Issue #433).
"""

from __future__ import annotations
from typing import Optional, Dict, Any
from src.locations.runner import run_regional_pipeline


def run_oakland_pipeline(
    live_oakland_price: Optional[float] = None,
    live_bayarea_price: Optional[float] = None,
    use_llm_api: bool = False,
    model_type: str = "ridge",
    log_wandb: bool = False
) -> Dict[str, Any]:
    """Executes the Oakland & SF Bay Area, CA (PADD 5) gas price prediction pipeline."""
    live_price = live_oakland_price if live_oakland_price is not None else live_bayarea_price
    return run_regional_pipeline(
        region_id="oakland",
        live_pump_price=live_price,
        use_llm_api=use_llm_api,
        model_type=model_type,
        log_wandb=log_wandb
    )


if __name__ == "__main__":
    run_oakland_pipeline()
