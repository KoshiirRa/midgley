#!/usr/bin/env python3
"""
scripts/clean_file_links.py
Audits and replaces local file:/// URLs with repository-relative or canonical URLs.
"""
import os
import re
import sys

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WIKI_DIR = r"c:\Users\concentus\Documents\midgley.wiki"

PATTERNS = [
    # Full Windows path with encoded or literal spaces
    re.compile(r'file:///c:/Users/concentus/Documents/Random(?:%20|\s)Ideas(?:%20|\s)-(?:%20|\s)LLM(?:%20|\s)Unleaded(?:%20|\s)Gas(?:%20|\s)Price(?:%20|\s)Prediction(?:%20|\s)Modelling/scratch/midgley\.wiki/([^\s\)\"\'`>]+)', re.IGNORECASE),
    re.compile(r'file:///c:/Users/concentus/Documents/Random(?:%20|\s)Ideas(?:%20|\s)-(?:%20|\s)LLM(?:%20|\s)Unleaded(?:%20|\s)Gas(?:%20|\s)Price(?:%20|\s)Prediction(?:%20|\s)Modelling/([^\s\)\"\'`>]+)', re.IGNORECASE),
    # file:///c:/... or file:///C:/... without the repo prefix
    re.compile(r'file:///[a-zA-Z]:/Users/[^\s\)\"\'`>]+/([^\s\)\"\'`>]+)', re.IGNORECASE),
    # file:///relative/path or file:///src/... or file:///docs/...
    re.compile(r'file:///([^\s\)\"\'`>]+)', re.IGNORECASE),
]

EXCLUDED_FILES = {
    'clean_file_links.py',
    'test_docs_links.py',
}

def clean_content(content: str, is_wiki: bool = False) -> tuple[str, int]:
    total_replacements = 0
    new_content = content
    
    # First handle wiki scratch links if any
    new_content, count = PATTERNS[0].subn(r'\1', new_content)
    total_replacements += count
    
    # Handle repo root links
    new_content, count = PATTERNS[1].subn(r'\1', new_content)
    total_replacements += count
    
    # Handle other local paths
    new_content, count = PATTERNS[2].subn(r'\1', new_content)
    total_replacements += count
    
    # Handle file:///docs/... etc.
    new_content, count = PATTERNS[3].subn(r'\1', new_content)
    total_replacements += count
    
    return new_content, total_replacements

def process_directory(base_dir: str, is_wiki: bool = False, apply_fix: bool = False):
    if not os.path.exists(base_dir):
        print(f"Directory not found: {base_dir}")
        return
    
    print(f"\nScanning: {base_dir} (is_wiki={is_wiki}, apply_fix={apply_fix})")
    matched_files = 0
    total_instances = 0
    
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in {'.git', '.venv', 'venv', 'env', '.env', 'node_modules', '.pytest_cache', '__pycache__', 'scratch', 'build', 'dist', 'site-packages', '.tox', '.mypy_cache', '.ruff_cache', '.gemini'}]
        for f in files:
            if f in EXCLUDED_FILES:
                continue
            if f.endswith(('.md', '.html', '.ts', '.py', '.json', '.yml', '.yaml', '.txt')):
                file_path = os.path.join(root, f)
                try:
                    with open(file_path, 'r', encoding='utf-8') as fp:
                        content = fp.read()
                except UnicodeDecodeError:
                    continue
                
                if 'file:///' in content:
                    new_content, count = clean_content(content, is_wiki=is_wiki)
                    if count > 0:
                        matched_files += 1
                        total_instances += count
                        rel_path = os.path.relpath(file_path, base_dir)
                        print(f"  {rel_path}: {count} replacements")
                        if apply_fix:
                            with open(file_path, 'w', encoding='utf-8', newline='\n') as fp:
                                fp.write(new_content)

    print(f"Total: {total_instances} instances in {matched_files} files.")

if __name__ == '__main__':
    apply_changes = "--write" in sys.argv
    process_directory(REPO_DIR, is_wiki=False, apply_fix=apply_changes)
    if os.path.exists(WIKI_DIR):
        process_directory(WIKI_DIR, is_wiki=True, apply_fix=apply_changes)
