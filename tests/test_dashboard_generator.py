import os
import sys
import pytest

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.dashboard_generator import (
    generate_public_dashboard,
    INDEX_PATH,
    NATIONAL_PATH,
    TULSA_PATH,
    NEWARK_PATH,
    MATH_PATH,
)


def test_dashboard_generation_and_math_katex():
    """Verify that generate_public_dashboard generates clean HTML files

    and that docs/math.html contains valid KaTeX markup without Python

    string escape character corruption (Issue #26).

    """
    # Execute public dashboard generation
    generate_public_dashboard()

    # Verify existence of all expected dashboard HTML files
    for path in [INDEX_PATH, NATIONAL_PATH, TULSA_PATH, NEWARK_PATH, MATH_PATH]:
        assert os.path.exists(path), f"Expected file does not exist: {path}"
        assert os.path.getsize(path) > 0, f"Generated file is empty: {path}"

    # Read generated docs/math.html content
    with open(MATH_PATH, "r", encoding="utf-8") as f:
        math_content = f.read()

    # Check for unwanted ASCII control characters in docs/math.html
    # (these indicate unescaped LaTeX backslashes evaluated in non-raw string literals)
    ctrl_chars = [
        ("\t", "Tab"),
        ("\f", "Formfeed"),
        ("\r", "Carriage Return"),
        ("\a", "Bell"),
        ("\b", "Backspace"),
    ]
    for char, name in ctrl_chars:
        count = math_content.count(char)
        assert count == 0, f"Found {count} unescaped '{name}' control character(s) in docs/math.html"

    # Verify presence of expected LaTeX macros in Sections 7, 8, and 9
    expected_macros = [
        r"\text",
        r"\frac",
        r"\right",
        r"\alpha",
        r"\beta",
        r"\boldsymbol",
        r"\times",
    ]
    for macro in expected_macros:
        assert macro in math_content, f"Expected LaTeX macro '{macro}' not found in docs/math.html"

    # Verify specific equations in Sections 07, 08, and 09
    # Section 07 (Equation 7.1)
    assert r"\mathbf{V}_{\text{Finlight}, t}" in math_content
    assert r"\text{REST}_{\text{Finlight}}" in math_content

    # Section 08 (Equation 8.1)
    assert r"\mathbf{M}_t = \mathbf{M}_{t-1} \cdot \exp\left(-\frac{\ln 2}{t_{1/2}}\right) + \mathbf{V}_t" in math_content

    # Section 09 (Equation 9.1)
    assert r"\min_{\boldsymbol{\beta}}" in math_content
    assert r"\alpha \|\boldsymbol{\beta}\|_2^2" in math_content
    assert r"\hat{P}_{\text{Metro Retail}, t+5}" in math_content
