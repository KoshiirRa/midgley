"""
tests/test_docs_links.py
Automated test suite verifying documentation link integrity and preventing
local file:/// URLs across markdown documentation, HTML templates, and code.
"""
import os
import re
import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    ".pytest_cache",
    "__pycache__",
    "scratch",
    ".gemini",
}

EXCLUDED_FILES = {
    "test_docs_links.py",
    "clean_file_links.py",
}

def get_tracked_docs_and_templates():
    """Collect all doc, template, and code files to inspect."""
    target_extensions = (".md", ".html", ".ts", ".py", ".json", ".yml", ".yaml")
    files_to_check = []
    
    for root, dirs, files in os.walk(REPO_ROOT):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for f in files:
            if f in EXCLUDED_FILES:
                continue
            if f.endswith(target_extensions):
                files_to_check.append(os.path.join(root, f))
                
    return sorted(files_to_check)

def test_no_local_file_urls_in_repo():
    """Assert 0 occurrences of local file:/// URLs across repository files (Issue #379)."""
    files = get_tracked_docs_and_templates()
    assert len(files) > 0, "Expected to find tracked files in repository"
    
    violations = []
    file_url_pattern = re.compile(r'file:///[^\s\)\"\'`>]+', re.IGNORECASE)
    
    for file_path in files:
        try:
            with open(file_path, "r", encoding="utf-8") as fp:
                content = fp.read()
        except UnicodeDecodeError:
            continue
            
        matches = file_url_pattern.findall(content)
        if matches:
            rel_path = os.path.relpath(file_path, REPO_ROOT)
            violations.append(f"{rel_path}: {len(matches)} occurrences ({matches[:2]})")
            
    assert not violations, f"Found local file:/// URLs in repository files:\n" + "\n".join(violations)

def test_dashboard_generator_does_not_emit_file_urls():
    """Verify that dashboard_generator and weekly_issue_reporter have no hardcoded file:/// strings."""
    for mod_name in ["src/dashboard_generator.py", "src/weekly_issue_reporter.py", "src/sources_generator.py"]:
        path = os.path.join(REPO_ROOT, mod_name)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fp:
                content = fp.read()
            assert "file:///" not in content, f"Hardcoded file:/// found in {mod_name}"
