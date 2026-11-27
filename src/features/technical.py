"""Technical momentum feature family wrapper (Issue #562)."""

from typing import Any
import pandas as pd

from src.features.base import FeatureFamily


class TechnicalMomentumFeatureFamily(FeatureFamily):
    """Computes technical momentum indicators (RSI, MACD, Bollinger Bands, ATR, spreads)."""

    name = "technical_momentum"

    def transform(self, df: pd.DataFrame, **context: Any) -> pd.DataFrame:
        from src.feature_engineering import compute_technical_momentum_indicators

        return compute_technical_momentum_indicators(df)
