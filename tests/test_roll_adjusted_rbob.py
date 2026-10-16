"""
Unit & Integration Tests for Roll-Adjusted RBOB Futures & Regional Wholesale Hub Mapping (Issue #444).
"""

import unittest
import numpy as np
import pandas as pd
from datetime import datetime
from src.data_ingestion import compute_roll_adjusted_rbob, fetch_regional_wholesale_spot_matrix


class TestRollAdjustedRBOB(unittest.TestCase):
    def test_roll_adjustment_eliminates_artificial_jumps(self):
        # Construct synthetic daily data across Feb -> Mar with a +15% expiry jump
        dates = pd.date_range(start="2024-02-15", end="2024-03-15", freq="B")
        prices = []
        for d in dates:
            if d.month == 2:
                prices.append(2.20 + np.random.normal(0, 0.01))
            else:
                # March jump to summer spec
                prices.append(2.55 + np.random.normal(0, 0.01))

        df = pd.DataFrame({"date": dates, "gasoline_rbob": prices})
        adjusted_df = compute_roll_adjusted_rbob(df, price_col="gasoline_rbob")

        self.assertIn("gasoline_rbob_roll_adj", adjusted_df.columns)
        self.assertIn("gasoline_rbob_roll_adj_ret", adjusted_df.columns)
        self.assertIn("summer_rbob_indicator", adjusted_df.columns)

        # Check that the roll adjusted series is smooth across the month boundary
        # Find index of March 1
        mar_idx = (adjusted_df["date"].dt.month == 3).idxmax()
        p_feb_last = adjusted_df["gasoline_rbob_roll_adj"].iloc[mar_idx - 1]
        p_mar_first = adjusted_df["gasoline_rbob_roll_adj"].iloc[mar_idx]
        roll_diff_pct = abs(p_mar_first - p_feb_last) / p_feb_last

        # The artificial 15% jump should be smoothed away
        self.assertLess(roll_diff_pct, 0.05, "Roll boundary return was not smoothed by backward ratio adjustment")

    def test_summer_indicator_dates(self):
        dates = pd.to_datetime(["2024-01-15", "2024-04-15", "2024-07-04", "2024-10-01"])
        df = pd.DataFrame({"date": dates, "gasoline_rbob": [2.2, 2.6, 2.7, 2.3]})
        adjusted_df = compute_roll_adjusted_rbob(df)

        indicators = adjusted_df["summer_rbob_indicator"].tolist()
        self.assertEqual(indicators, [0, 1, 1, 0])

    def test_fetch_regional_wholesale_spot_matrix(self):
        spot_matrix = fetch_regional_wholesale_spot_matrix(start_date="2024-01-01", end_date="2024-01-10")
        self.assertIsInstance(spot_matrix, pd.DataFrame)
        self.assertFalse(spot_matrix.empty)
        self.assertIn("date", spot_matrix.columns)
        numeric_cols = [
            "spot_ny_harbor_dgasnyh",
            "spot_us_gulf_coast_dgasusgulf",
            "spot_la_carbob",
            "spot_tulsa_group3",
            "spot_cincinnati_chicago_cbob"
        ]
        for col in numeric_cols:
            self.assertIn(col, spot_matrix.columns)
            self.assertTrue((spot_matrix[col] > 0).all())


if __name__ == "__main__":
    unittest.main()
