"""Base abstractions for composable point-in-time FeatureFamily pipelines (Issue #562)."""

from abc import ABC, abstractmethod
from typing import Any, List
import pandas as pd


class FeatureFamily(ABC):
    """Abstract base class for a modular, point-in-time safe feature calculation family."""

    name: str = "base"

    @abstractmethod
    def transform(self, df: pd.DataFrame, **context: Any) -> pd.DataFrame:
        """Applies this feature family to ``df`` without mutating future observations."""


class FeaturePipeline:
    """Composes an ordered sequence of FeatureFamily transforms."""

    def __init__(self, families: List[FeatureFamily]) -> None:
        self.families = list(families)

    def run(self, df: pd.DataFrame, **context: Any) -> pd.DataFrame:
        result = df
        for family in self.families:
            result = family.transform(result, **context)
        return result
