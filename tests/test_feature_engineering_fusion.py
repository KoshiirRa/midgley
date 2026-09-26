"""
Unit tests for Feature Engineering Qualitative Event Fusion (Issue #355).
Validates:
1. Multi-event dates do NOT duplicate rows (strict 1-to-1 merge).
2. Weekend/holiday events (Sat/Sun) are forward-mapped to the next trading session.
3. Multiple events on the same trading day are summed and clamped to valid bounds.
4. Continuous time decay uses elapsed calendar days (dt) rather than discrete row steps.
"""

import unittest
import numpy as np
import pandas as pd
from src.feature_engineering import create_feature_matrix, CATEGORY_HALF_LIVES_DAYS


class TestFeatureEngineeringFusion(unittest.TestCase):

    def setUp(self):
        # 60 business days of synthetic market data starting on a Monday
        # 2026-01-05 is a Monday
        self.dates = pd.date_range('2026-01-05', periods=60, freq='B')
        prices = 2.50 + np.sin(np.linspace(0, 6, 60)) * 0.10
        self.market_df = pd.DataFrame({
            'date': self.dates,
            'gasoline_rbob': prices,
            'wti_crude': prices * 30
        })

    def test_no_row_duplication_on_multi_event_dates(self):
        """Verify that multiple qualitative events on the same date do NOT duplicate dataframe rows."""
        monday_date = self.dates[0]  # 2026-01-05
        events_df = pd.DataFrame([
            {
                'date': monday_date,
                'headline': 'OPEC announces surprise production cut',
                'geopolitical_risk': 0.8,
                'supply_disruption': 0.5,
                'demand_sentiment': 0.2,
                'opec_action': 0.9,
                'overall_price_pressure': 0.7
            },
            {
                'date': monday_date,
                'headline': 'Red Sea tanker attacked by drones',
                'geopolitical_risk': 0.9,
                'supply_disruption': 0.4,
                'demand_sentiment': 0.0,
                'opec_action': 0.0,
                'overall_price_pressure': 0.6
            },
            {
                'date': monday_date,
                'headline': 'Refinery flaring in Baytown reported',
                'geopolitical_risk': 0.1,
                'supply_disruption': 0.7,
                'demand_sentiment': -0.1,
                'opec_action': 0.0,
                'overall_price_pressure': 0.4
            }
        ])

        feat_df_no_events = create_feature_matrix(self.market_df, events_df=None, forecast_horizon=5)
        feat_df = create_feature_matrix(self.market_df, events_df=events_df, forecast_horizon=5)

        # Row count must match baseline exactly without duplicates (len(market_df) - forecast_horizon)
        self.assertEqual(len(feat_df), len(feat_df_no_events))
        self.assertEqual(len(feat_df), len(self.market_df) - 5)
        # No duplicate dates
        self.assertEqual(feat_df['date'].duplicated().sum(), 0)

        # Multi-event aggregation checks
        # overall_price_pressure sum = 0.7 + 0.6 + 0.4 = 1.7 -> clipped to 1.0
        self.assertAlmostEqual(feat_df.loc[0, 'event_overall_price_pressure'], 1.0, places=4)
        # supply_disruption sum = 0.5 + 0.4 + 0.7 = 1.6 -> clipped to 1.0
        self.assertAlmostEqual(feat_df.loc[0, 'event_supply_disruption'], 1.0, places=4)

    def test_weekend_events_forward_mapping(self):
        """Verify that weekend (Saturday/Sunday) events are forward-mapped to Monday trading session."""
        # 2026-01-10 is Saturday, 2026-01-11 is Sunday, 2026-01-12 is Monday (which is self.dates[5])
        saturday = pd.Timestamp('2026-01-10')
        sunday = pd.Timestamp('2026-01-11')
        monday = pd.Timestamp('2026-01-12')

        events_df = pd.DataFrame([
            {
                'date': saturday,
                'headline': 'Weekend pipeline shutdown',
                'geopolitical_risk': 0.4,
                'supply_disruption': 0.6,
                'demand_sentiment': 0.0,
                'opec_action': 0.0,
                'overall_price_pressure': 0.5
            },
            {
                'date': sunday,
                'headline': 'Sunday emergency OPEC meeting',
                'geopolitical_risk': 0.3,
                'supply_disruption': 0.2,
                'demand_sentiment': 0.1,
                'opec_action': 0.7,
                'overall_price_pressure': 0.4
            }
        ])

        feat_df_no_events = create_feature_matrix(self.market_df, events_df=None, forecast_horizon=5)
        feat_df = create_feature_matrix(self.market_df, events_df=events_df, forecast_horizon=5)

        # Row count must match baseline
        self.assertEqual(len(feat_df), len(feat_df_no_events))
        self.assertEqual(len(feat_df), len(self.market_df) - 5)

        # Check Monday row (index 5)
        monday_idx = feat_df.index[feat_df['date'] == monday].tolist()[0]
        self.assertEqual(monday_idx, 5)

        # Prior week (indices 0..4) should have 0.0 event shock
        for i in range(5):
            self.assertEqual(feat_df.loc[i, 'event_supply_disruption'], 0.0)

        # Monday (index 5) should have accumulated weekend shocks
        # supply_disruption = 0.6 + 0.2 = 0.8
        self.assertAlmostEqual(feat_df.loc[5, 'event_supply_disruption'], 0.8, places=4)
        # opec_action = 0.0 + 0.7 = 0.7
        self.assertAlmostEqual(feat_df.loc[5, 'event_opec_action'], 0.7, places=4)
        # overall_price_pressure = 0.5 + 0.4 = 0.9
        self.assertAlmostEqual(feat_df.loc[5, 'event_overall_price_pressure'], 0.9, places=4)

    def test_calendar_elapsed_decay_over_weekend(self):
        """
        Verify that exponential decay across a weekend (Friday to Monday, dt=3 days)
        decays by exp(-3*lambda), whereas Monday to Tuesday (dt=1 day) decays by exp(-1*lambda).
        """
        # Place a single shock on Friday 2026-01-09 (index 4)
        friday = pd.Timestamp('2026-01-09')
        events_df = pd.DataFrame([{
            'date': friday,
            'geopolitical_risk': 1.0,
            'supply_disruption': 0.0,
            'demand_sentiment': 0.0,
            'opec_action': 0.0,
            'overall_price_pressure': 1.0
        }])

        feat_df = create_feature_matrix(self.market_df, events_df=events_df, forecast_horizon=5)

        # Friday is index 4, Monday is index 5, Tuesday is index 6
        friday_idx = 4
        monday_idx = 5
        tuesday_idx = 6

        # Friday shock value
        val_fri = feat_df.loc[friday_idx, 'event_geopolitical_risk']
        val_mon = feat_df.loc[monday_idx, 'event_geopolitical_risk']
        val_tue = feat_df.loc[tuesday_idx, 'event_geopolitical_risk']

        # Check ratio val_mon / val_fri: should equal exp(-ln(2)*3 / effective_half_life)
        decay_weekend_ratio = val_mon / val_fri
        decay_weekday_ratio = val_tue / val_mon

        # Weekend decay (3 days) must be strictly greater decay (smaller retention ratio) than weekday decay (1 day)
        self.assertLess(decay_weekend_ratio, decay_weekday_ratio)

        # Mathematically: decay_weekend_ratio should equal (decay_weekday_ratio)^3
        self.assertAlmostEqual(decay_weekend_ratio, decay_weekday_ratio ** 3, places=4)


if __name__ == '__main__':
    unittest.main()
