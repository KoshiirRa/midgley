"""
Unit test suite for Fireworks Tech Graph Architecture Diagram Generator (tests/test_diagram_generator.py)
"""

import os
import xml.etree.ElementTree as ET
import pytest
from src.fireworks_tech_graph import (
    generate_multi_agent_pipeline_svg,
    generate_regional_metro_svg,
    validate_svg_content,
    generate_architecture_diagrams,
)


def test_generate_multi_agent_pipeline_svg():
    svg_str = generate_multi_agent_pipeline_svg()
    assert isinstance(svg_str, str)
    assert len(svg_str) > 1000
    assert svg_str.startswith("<svg")
    assert svg_str.endswith("</svg>")
    assert validate_svg_content(svg_str) is True

    # Check key architectural stages in text
    assert "MIDGLEY UNLEADED GASOLINE FORECASTING ENGINE" in svg_str
    assert "STAGE 1 &amp; 2" in svg_str or "STAGE 1 & 2" in svg_str
    assert "STAGE 3" in svg_str
    assert "STAGE 4" in svg_str
    assert "STAGE 5" in svg_str
    assert "STAGE 6" in svg_str
    assert "STAGE 7" in svg_str
    assert "STAGE 8" in svg_str
    assert "data/prediction_history.csv" in svg_str


def test_generate_regional_metro_svg():
    svg_str = generate_regional_metro_svg()
    assert isinstance(svg_str, str)
    assert len(svg_str) > 1000
    assert svg_str.startswith("<svg")
    assert svg_str.endswith("</svg>")
    assert validate_svg_content(svg_str) is True

    # Check key metro hubs in text
    assert "REGIONAL METRO CALIBRATION HUBS" in svg_str
    assert "Tulsa Metro, OK" in svg_str
    assert "Newark Metro, DE" in svg_str
    assert "Cincinnati OH / NKY" in svg_str
    assert "Charlotte &amp; Greenville" in svg_str or "Charlotte & Greenville" in svg_str
    assert "Oakland &amp; SF Bay" in svg_str or "Oakland & SF Bay" in svg_str
    assert "Port St. Lucie Metro, FL" in svg_str
    assert "ULSD Distillate Fuel Engine" in svg_str


def test_generate_architecture_diagrams_files(tmp_path):
    output_dir = str(tmp_path / "assets")
    res = generate_architecture_diagrams(output_dir=output_dir)

    assert "multi_agent_architecture.svg" in res
    assert "regional_metro_architecture.svg" in res

    for fname, fpath in res.items():
        assert os.path.exists(fpath)
        assert os.path.getsize(fpath) > 1000
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
            assert validate_svg_content(content) is True
