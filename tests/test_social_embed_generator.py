"""
Unit Tests for Social Embed Image Generator & Meta Tag Injection (tests/test_social_embed_generator.py)
"""

import os
import glob
import pytest
from PIL import Image

from src.social_embed_generator import generate_social_embed_images, render_single_embed_card, LOCALE_SPECS
from src.dashboard_generator import get_head_meta_tags, generate_public_dashboard, DOCS_DIR


def test_get_head_meta_tags():
    """Test get_head_meta_tags helper formatting."""
    tags = get_head_meta_tags(
        title="Test Title",
        description="Test Description",
        canonical_path="tulsa.html",
        image_filename="tulsa.png",
        theme_color="#10b981"
    )
    assert '<meta property="og:site_name" content="Midgley Gas Price Prediction AI">' in tags
    assert '<meta property="og:title" content="Test Title">' in tags
    assert '<meta property="og:description" content="Test Description">' in tags
    assert '<meta property="og:url" content="https://koshiirra.github.io/midgley/tulsa.html">' in tags
    assert '<meta property="og:image" content="https://koshiirra.github.io/midgley/assets/embeds/tulsa.png">' in tags
    assert '<meta property="og:image:width" content="1200">' in tags
    assert '<meta property="og:image:height" content="630">' in tags
    assert '<meta name="twitter:card" content="summary_large_image">' in tags
    assert '<meta name="theme-color" content="#10b981">' in tags


def test_generate_social_embed_images(tmp_path):
    """Test automated rendering of 1200x630 dark-mode PNG cards across all 10 locale routes."""
    out_dir = str(tmp_path / "embeds")
    results = generate_social_embed_images(output_dir=out_dir)

    assert len(results) == len(LOCALE_SPECS)
    for locale_key, img_path in results.items():
        assert os.path.exists(img_path)
        with Image.open(img_path) as img:
            width, height = img.size
            assert width == 1200, f"Expected width 1200 for {locale_key}, got {width}"
            assert height == 630, f"Expected height 630 for {locale_key}, got {height}"


def test_dashboard_generator_head_meta_injection():
    """Test that generate_public_dashboard injects Open Graph and Twitter meta tags across HTML files in docs/."""
    generate_public_dashboard()

    html_files = [
        os.path.join(DOCS_DIR, "index.html"),
        os.path.join(DOCS_DIR, "national.html"),
        os.path.join(DOCS_DIR, "tulsa.html"),
        os.path.join(DOCS_DIR, "newark.html"),
        os.path.join(DOCS_DIR, "cincinnati.html"),
        os.path.join(DOCS_DIR, "greenville.html"),
        os.path.join(DOCS_DIR, "charlotte.html"),
        os.path.join(DOCS_DIR, "oakland.html"),
        os.path.join(DOCS_DIR, "bayarea.html"),
        os.path.join(DOCS_DIR, "math.html"),
        os.path.join(DOCS_DIR, "technical_breakdown.html"),
    ]

    for filepath in html_files:
        assert os.path.exists(filepath), f"Expected file {filepath} to exist"
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            assert '<meta property="og:site_name"' in content, f"Missing og:site_name in {filepath}"
            assert '<meta property="og:title"' in content, f"Missing og:title in {filepath}"
            assert '<meta property="og:image"' in content, f"Missing og:image in {filepath}"
            assert '<meta name="twitter:card" content="summary_large_image"' in content, f"Missing twitter:card in {filepath}"
            assert '<meta name="theme-color"' in content, f"Missing theme-color in {filepath}"
