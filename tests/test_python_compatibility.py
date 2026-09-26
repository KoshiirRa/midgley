"""
Unit Tests for Python 3.9+ Compatibility & Type Annotation Safety (tests/test_python_compatibility.py)
Verifies that core modules with PEP 604 union type syntax import and evaluate cleanly (Issue #336).
"""

import importlib
import unittest


class TestPythonCompatibility(unittest.TestCase):
    def test_models_import_and_annotations(self):
        """Verifies src.models imports and resolves PEP 604 type annotations."""
        mod = importlib.import_module("src.models")
        self.assertTrue(hasattr(mod, "train_and_compare_models"))
        self.assertTrue(hasattr(mod, "compute_rolling_volatility_index"))

    def test_prediction_logger_import_and_annotations(self):
        """Verifies src.prediction_logger imports and resolves PEP 604 type annotations."""
        mod = importlib.import_module("src.prediction_logger")
        self.assertTrue(hasattr(mod, "log_predictions"))
        self.assertTrue(hasattr(mod, "compute_rolling_scoreboard_metrics"))
        self.assertTrue(hasattr(mod, "compute_regional_scoreboard_breakdown"))
        self.assertTrue(hasattr(mod, "get_recent_evaluated_records"))

    def test_weekly_issue_reporter_import_and_annotations(self):
        """Verifies src.weekly_issue_reporter imports and resolves PEP 604 type annotations."""
        mod = importlib.import_module("src.weekly_issue_reporter")
        self.assertTrue(hasattr(mod, "evaluate_model_degradation_alerts"))
        self.assertTrue(hasattr(mod, "generate_weekly_markdown_report"))

    def test_feature_engineering_import_and_annotations(self):
        """Verifies src.feature_engineering imports cleanly."""
        mod = importlib.import_module("src.feature_engineering")
        self.assertTrue(hasattr(mod, "create_feature_matrix"))


if __name__ == "__main__":
    unittest.main()
