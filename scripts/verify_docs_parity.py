#!/usr/bin/env python3
"""
scripts/verify_docs_parity.py
Verifies and enforces byte-for-byte parity between root documentation files
and their mirrors in docs/ to eliminate content drift (Issue #337).
"""
import os
import sys
import difflib

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

DOC_PAIRS = [
    ("README.md", "docs/README.md"),
    ("SELF_HOSTING.md", "docs/SELF_HOSTING.md"),
    ("API.md", "docs/API.md"),
    ("ARCHITECTURE.md", "docs/ARCHITECTURE.md"),
    ("DESIGN.md", "docs/DESIGN.md"),
    ("AGENTS.md", "docs/AGENTS.md"),
    ("AI_DISCLOSURE.md", "docs/AI_DISCLOSURE.md"),
]


def sync_docs(repo_root: str = REPO_ROOT) -> int:
    """Copies canonical root documentation files into docs/ mirrors."""
    synced = 0
    for root_rel, docs_rel in DOC_PAIRS:
        root_path = os.path.join(repo_root, root_rel)
        docs_path = os.path.join(repo_root, docs_rel)
        
        if not os.path.exists(root_path):
            print(f"[!] Canonical root source not found: {root_rel}")
            continue
            
        with open(root_path, "r", encoding="utf-8") as f_in:
            content = f_in.read()
            
        os.makedirs(os.path.dirname(docs_path), exist_ok=True)
        with open(docs_path, "w", encoding="utf-8", newline="\n") as f_out:
            f_out.write(content)
            
        print(f"[+] Synchronized {root_rel} -> {docs_rel}")
        synced += 1
    return synced


def check_docs_parity(repo_root: str = REPO_ROOT, verbose: bool = True) -> tuple[bool, list[str]]:
    """Checks whether root docs and docs/ mirrors are in 100% byte-for-byte parity."""
    all_matched = True
    divergences = []
    
    for root_rel, docs_rel in DOC_PAIRS:
        root_path = os.path.join(repo_root, root_rel)
        docs_path = os.path.join(repo_root, docs_rel)
        
        if not os.path.exists(root_path):
            all_matched = False
            msg = f"Missing canonical root document: {root_rel}"
            divergences.append(msg)
            if verbose:
                print(f"[FAIL] {msg}")
            continue
            
        if not os.path.exists(docs_path):
            all_matched = False
            msg = f"Missing mirrored document in docs/: {docs_rel}"
            divergences.append(msg)
            if verbose:
                print(f"[FAIL] {msg}")
            continue
            
        with open(root_path, "r", encoding="utf-8") as f1, open(docs_path, "r", encoding="utf-8") as f2:
            lines1 = f1.readlines()
            lines2 = f2.readlines()
            
        if lines1 != lines2:
            all_matched = False
            diff = list(difflib.unified_diff(
                lines1, lines2, 
                fromfile=root_rel, 
                tofile=docs_rel, 
                n=2
            ))
            msg = f"Content drift detected between {root_rel} and {docs_rel} ({len(diff)} diff lines)"
            divergences.append(msg)
            if verbose:
                print(f"[FAIL] {msg}")
                for line in diff[:10]:
                    print(f"  {line.rstrip()}")
                if len(diff) > 10:
                    print(f"  ... ({len(diff) - 10} more diff lines)")
        else:
            if verbose:
                print(f"[PASS] {root_rel} == {docs_rel} (100% parity)")
                
    return all_matched, divergences


if __name__ == "__main__":
    if "--sync" in sys.argv:
        sync_docs()
        print("\nAll documentation mirrors updated successfully.")
        sys.exit(0)
    else:
        matched, errors = check_docs_parity(verbose=True)
        if not matched:
            print(f"\n[!] Documentation parity check failed with {len(errors)} divergence(s).")
            print("    Run 'python scripts/verify_docs_parity.py --sync' to synchronize.")
            sys.exit(1)
        else:
            print("\n[OK] All documentation files are in 100% parity.")
            sys.exit(0)
