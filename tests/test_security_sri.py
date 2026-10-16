"""
Unit Tests for Subresource Integrity (SRI), CSP, and Secret Redaction (tests/test_security_sri.py)
Validates Issue #570: SRI integrity hashes, strict CSP headers/meta, and secret redaction.
"""

import re
import pytest
from src.key_manager import redact_secrets
from src.dashboard_generator import get_head_meta_tags
from src.sources_generator import SOURCES_HTML_TEMPLATE


def test_redact_secrets_masks_tokens():
    raw_gh_token = "ghp_1234567890abcdefghijklmnopqrstuvwxyzAB"
    raw_mg_token = "mg_prod_12345678_abcdef0123456789abcdef0123456789"
    raw_sk_token = "sk-1234567890abcdefghijklmnopqrstuvwxyz"
    
    text = f"Error in execution with token {raw_gh_token} and key {raw_mg_token} or {raw_sk_token}"
    redacted = redact_secrets(text)
    
    assert raw_gh_token not in redacted
    assert raw_mg_token not in redacted
    assert raw_sk_token not in redacted
    assert "[REDACTED]" in redacted


def test_head_meta_tags_include_csp():
    meta_html = get_head_meta_tags("Test Title", "Test Description")
    assert "Content-Security-Policy" in meta_html
    assert "default-src" in meta_html


def test_sources_html_includes_sri_and_crossorigin():
    assert 'integrity="sha384-GvrOXuhMATgEsSwCs4smul74iXGOixntILdUW9XmUC6+HX0sLNAK3q71HotJqlAn"' in SOURCES_HTML_TEMPLATE
    assert 'integrity="sha384-cpW21h6RZv/phavutF+AuVYrr+dA8xD9zs6FwLpaCct6O9ctzYFfFr4dgmgccOTx"' in SOURCES_HTML_TEMPLATE
    assert 'integrity="sha384-+VBxd3r6XgURycqtZ117nYw44OOcIax56Z4dCRWbxyPt0Koah1uHoK0o4+/RRE05"' in SOURCES_HTML_TEMPLATE
    assert 'crossorigin="anonymous"' in SOURCES_HTML_TEMPLATE
