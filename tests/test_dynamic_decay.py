"""
Unit tests for Dynamic Category-Specific Event Shock Decay Half-Lives (Issue #168).
Verifies that event features decay according to their taxonomy-specific half-life curves:
- supply_disruption: 14.0 days (structural physical outages)
- geopolitical_risk: 7.0 days
- opec_action: 5.0 days
- demand_sentiment: 4.0 days
- overall_price_pressure: 2.5 days (executive social posts / headlines)
"""

import unittest
import pandas as pd
import numpy as np
from src.feature_engineering import create_feature_matrix, CATEGORY_HALF_LIVES_DAYS

class TestDynamicCategoryDecay(unittest.TestCase):

    def setUp(self):
        # Create 60 business days of synthetic market data to accommodate 30-day rolling indicators
        dates = pd.date_range('2026-01-01', periods=60, freq='B')
        prices = 2.50 + np.sin(np.linspace(0, 6, 60)) * 0.10
        self.market_df = pd.DataFrame({
            'date': dates,
            'gasoline_rbob': prices,
            'wti_crude': prices * 30
        })

    def test_category_half_lives_dict_structure(self):
        """Verify CATEGORY_HALF_LIVES_DAYS constant contains all expected event categories."""
        expected_keys = ['supply_disruption', 'geopolitical_risk', 'opec_action', 'demand_sentiment', 'overall_price_pressure']
        for key in expected_keys:
            self.assertIn(key, CATEGORY_HALF_LIVES_DAYS)
            self.assertGreater(CATEGORY_HALF_LIVES_DAYS[key], 0.0)

        # Confirm structural ordering (supply_disruption longest, overall_price_pressure shortest)
        self.assertGreater(CATEGORY_HALF_LIVES_DAYS['supply_disruption'], CATEGORY_HALF_LIVES_DAYS['geopolitical_risk'])
        self.assertGreater(CATEGORY_HALF_LIVES_DAYS['geopolitical_risk'], CATEGORY_HALF_LIVES_DAYS['opec_action'])
        self.assertGreater(CATEGORY_HALF_LIVES_DAYS['opec_action'], CATEGORY_HALF_LIVES_DAYS['demand_sentiment'])
        self.assertGreater(CATEGORY_HALF_LIVES_DAYS['demand_sentiment'], CATEGORY_HALF_LIVES_DAYS['overall_price_pressure'])

    def test_dynamic_decay_retention_persistence(self):
        """
        Verify that a 1.0 point shock on Day 1 for supply_disruption (t1/2 = 14d)
        retains significantly more memory after 10 days than overall_price_pressure (t1/2 = 2.5d).
        """
        events_df = pd.DataFrame({
            'date': [self.market_df['date'].iloc[0]],
            'geopolitical_risk': [1.0],
            'supply_disruption': [1.0],
            'demand_sentiment': [1.0],
            'opec_action': [1.0],
            'overall_price_pressure': [1.0]
        })

        df_feat = create_feature_matrix(self.market_df, events_df=events_df, forecast_horizon=5)

        # Check memory on day 10 (index ~ 10)
        day_10_idx = 10
        supply_mem = df_feat.loc[day_10_idx, 'event_supply_disruption']
        pressure_mem = df_feat.loc[day_10_idx, 'event_overall_price_pressure']

        self.assertGreater(supply_mem, pressure_mem)
        # supply_disruption (14d half life) should retain > 2x the memory of overall_price_pressure (2.5d half life)
        self.assertGreater(supply_mem / (pressure_mem + 1e-9), 2.0)

if __name__ == '__main__':
    unittest.main()
