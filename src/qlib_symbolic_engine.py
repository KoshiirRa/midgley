"""
Qlib Symbolic Domain Expression Engine
Provides point-in-time compliant rolling time-series operators (Ref, Mean, Std, Delta, Roc, ZScore, Slope, Corr, Rank)
and AST-based expression parsing for financial factor engineering inspired by Microsoft Research Qlib.
"""

import ast
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Union, List

logger = logging.getLogger(__name__)

# Point-in-time safety limit: Maximum allowed window size to prevent memory explosion
MAX_ROLLING_WINDOW = 252


def ref(series: pd.Series, lag: int = 1) -> pd.Series:
    """Ref(x, d): Shifts series x backward by lag d (d >= 0). Ensures no lookahead leakage."""
    if lag < 0:
        raise ValueError(f"Lookahead violation: lag must be >= 0, got {lag}")
    return series.shift(lag)


def mean_op(series: pd.Series, window: int = 5) -> pd.Series:
    """Mean(x, d): Rolling mean over d periods."""
    window = max(1, min(int(window), MAX_ROLLING_WINDOW))
    return series.rolling(window=window, min_periods=1).mean()


def std_op(series: pd.Series, window: int = 5) -> pd.Series:
    """Std(x, d): Rolling standard deviation over d periods."""
    window = max(1, min(int(window), MAX_ROLLING_WINDOW))
    return series.rolling(window=window, min_periods=1).std().fillna(0.0)


def min_op(series: pd.Series, window: int = 5) -> pd.Series:
    """Min(x, d): Rolling minimum over d periods."""
    window = max(1, min(int(window), MAX_ROLLING_WINDOW))
    return series.rolling(window=window, min_periods=1).min()


def max_op(series: pd.Series, window: int = 5) -> pd.Series:
    """Max(x, d): Rolling maximum over d periods."""
    window = max(1, min(int(window), MAX_ROLLING_WINDOW))
    return series.rolling(window=window, min_periods=1).max()


def delta_op(series: pd.Series, period: int = 1) -> pd.Series:
    """Delta(x, d): x_t - x_{t-d}."""
    period = max(0, int(period))
    return series - series.shift(period)


def roc_op(series: pd.Series, period: int = 1) -> pd.Series:
    """Roc(x, d): Rate of change (x_t - x_{t-d}) / (|x_{t-d}| + eps)."""
    period = max(0, int(period))
    prev = series.shift(period)
    return (series - prev) / (prev.abs() + 1e-8)


def zscore_op(series: pd.Series, window: int = 20) -> pd.Series:
    """ZScore(x, d): Normalized rolling Z-score (x - Mean(x, d)) / (Std(x, d) + eps)."""
    window = max(1, min(int(window), MAX_ROLLING_WINDOW))
    m = mean_op(series, window)
    s = std_op(series, window)
    return (series - m) / (s + 1e-8)


def slope_op(series: pd.Series, window: int = 10) -> pd.Series:
    """Slope(x, d): Rolling OLS linear regression slope of x over d periods."""
    window = max(2, min(int(window), MAX_ROLLING_WINDOW))
    x_axis = np.arange(window)
    x_mean = x_axis.mean()
    x_var = ((x_axis - x_mean) ** 2).sum()

    def _calc_slope(s):
        if len(s) < 2:
            return 0.0
        n = len(s)
        if n != window:
            x_sub = np.arange(n)
            xm = x_sub.mean()
            xv = ((x_sub - xm) ** 2).sum()
            if xv == 0:
                return 0.0
            return float(((x_sub - xm) * (s - s.mean())).sum() / xv)
        return float(((x_axis - x_mean) * (s - s.mean())).sum() / x_var)

    return series.rolling(window=window, min_periods=2).apply(_calc_slope, raw=False).fillna(0.0)


def corr_op(series1: pd.Series, series2: pd.Series, window: int = 20) -> pd.Series:
    """Corr(x, y, d): Rolling Pearson correlation between x and y over d periods."""
    window = max(2, min(int(window), MAX_ROLLING_WINDOW))
    return series1.rolling(window=window, min_periods=2).corr(series2).fillna(0.0)


def rank_op(series: pd.Series, window: int = 20) -> pd.Series:
    """Rank(x, d): Rolling percentile rank normalized between 0.0 and 1.0."""
    window = max(1, min(int(window), MAX_ROLLING_WINDOW))

    def _calc_rank(s):
        if len(s) <= 1:
            return 0.5
        val = s.iloc[-1]
        return float((s <= val).mean())

    return series.rolling(window=window, min_periods=1).apply(_calc_rank, raw=False).fillna(0.5)


# Function mapping dictionary for AST evaluator
SYMBOLIC_OPERATORS: Dict[str, Any] = {
    "Ref": ref,
    "Mean": mean_op,
    "Std": std_op,
    "Min": min_op,
    "Max": max_op,
    "Delta": delta_op,
    "Roc": roc_op,
    "ZScore": zscore_op,
    "Slope": slope_op,
    "Corr": corr_op,
    "Rank": rank_op,
    "Add": lambda x, y: x + y,
    "Sub": lambda x, y: x - y,
    "Mul": lambda x, y: x * y,
    "Div": lambda x, y: x / (y.abs() + 1e-8),
    "Abs": lambda x: x.abs(),
    "Sign": lambda x: np.sign(x),
    "Log": lambda x: np.log1p(x.abs()),
}


class ASTEvaluator(ast.NodeVisitor):
    """
    AST-based safe evaluator for Qlib symbolic expressions.
    Prevents arbitrary Python code execution while allowing complex multi-operator factor formulas.
    """

    def __init__(self, df: pd.DataFrame):
        self.df = df

    def evaluate(self, expr_str: str) -> pd.Series:
        expr_str = expr_str.strip()
        try:
            tree = ast.parse(expr_str, mode="eval")
            res = self.visit(tree.body)
            if isinstance(res, (int, float)):
                return pd.Series(res, index=self.df.index)
            return res.fillna(0.0)
        except Exception as e:
            logger.error(f"Error evaluating Qlib expression '{expr_str}': {e}")
            return pd.Series(0.0, index=self.df.index)

    def visit_Name(self, node: ast.Name):
        if node.id in self.df.columns:
            return self.df[node.id].astype(float)
        elif node.id in SYMBOLIC_OPERATORS:
            return SYMBOLIC_OPERATORS[node.id]
        else:
            raise NameError(f"Unknown column or operator in expression: '{node.id}'")

    def visit_Call(self, node: ast.Call):
        func = self.visit(node.func)
        args = [self.visit(arg) for arg in node.args]

        # Convert constant AST arguments (int/float)
        processed_args = []
        for arg in args:
            if isinstance(arg, pd.Series):
                processed_args.append(arg)
            elif callable(arg):
                processed_args.append(arg)
            else:
                processed_args.append(arg)

        return func(*processed_args)

    def visit_BinOp(self, node: ast.BinOp):
        left = self.visit(node.left)
        right = self.visit(node.right)

        if isinstance(node.op, ast.Add):
            return left + right
        elif isinstance(node.op, ast.Sub):
            return left - right
        elif isinstance(node.op, ast.Mult):
            return left * right
        elif isinstance(node.op, ast.Div):
            if isinstance(right, pd.Series):
                return left / (right.abs() + 1e-8)
            return left / (abs(right) + 1e-8)
        elif isinstance(node.op, ast.Pow):
            return left ** right
        else:
            raise TypeError(f"Unsupported binary operator: {type(node.op)}")

    def visit_UnaryOp(self, node: ast.UnaryOp):
        operand = self.visit(node.operand)
        if isinstance(node.op, ast.USub):
            return -operand
        elif isinstance(node.op, ast.UAdd):
            return operand
        else:
            raise TypeError(f"Unsupported unary operator: {type(node.op)}")

    def visit_Constant(self, node: ast.Constant):
        return node.value

    def visit_Num(self, node: ast.Num):  # Python 3.7 compatibility
        return node.n


class QlibSymbolicEngine:
    """
    Qlib Symbolic Factor Engine.
    Executes and validates rolling domain expressions on quantitative market DataFrames.
    """

    def __init__(self):
        self.operators = SYMBOLIC_OPERATORS

    def evaluate_expression(self, expression: str, df: pd.DataFrame) -> pd.Series:
        """
        Parses and evaluates a single symbolic factor expression over a DataFrame.
        Guarantees non-lookahead point-in-time calculation.
        """
        evaluator = ASTEvaluator(df)
        return evaluator.evaluate(expression)

    def batch_evaluate(self, expressions: List[str], df: pd.DataFrame) -> pd.DataFrame:
        """
        Evaluates a list of symbolic factor expressions and returns a DataFrame of factor series.
        """
        result_df = pd.DataFrame(index=df.index)
        for idx, expr in enumerate(expressions):
            col_name = f"qlib_factor_{idx+1}"
            result_df[col_name] = self.evaluate_expression(expr, df)
        return result_df
