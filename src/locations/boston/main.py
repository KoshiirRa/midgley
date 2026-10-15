"""
Boston Regional Master Execution Script (src/locations/boston/main.py)
Consolidated parameterized runner delegating to src/locations/runner.py (Issue #433, Issue #619).
"""

from __future__ import annotations
from typing import Optional, Dict, Any
from src.locations.runner import run_regional_pipeline


def run_boston_pipeline(
    live_pump_price: Optional[float] = None,
    use_llm_api: bool = False,
    model_type: str = "ridge",
    log_wandb: bool = False
) -> Dict[str, Any]:
    """Executes the Boston Metro & New England Regional Hub gas price prediction pipeline."""
    return run_regional_pipeline(
        region_id="boston",
        live_pump_price=live_pump_price,
        use_llm_api=use_llm_api,
        model_type=model_type,
        log_wandb=log_wandb
    )


if __name__ == "__main__":
    run_boston_pipeline()
