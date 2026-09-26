"""
tests/test_docs_parity.py
Automated test suite asserting 100% byte-for-byte parity between root
documentation files and their docs/ mirrors (Issue #337).
"""
import os
import pytest
from scripts.verify_docs_parity import DOC_PAIRS, check_docs_parity, REPO_ROOT


def test_core_docs_parity():
    """Assert all 6 core documentation pairs in root and docs/ are in 100% parity."""
    matched, errors = check_docs_parity(repo_root=REPO_ROOT, verbose=False)
    assert matched, (
        f"Documentation content drift detected between root and docs/ mirrors:\n"
        + "\n".join(errors)
        + "\nRun 'python scripts/verify_docs_parity.py --sync' to synchronize."
    )


@pytest.mark.parametrize("root_rel, docs_rel", DOC_PAIRS)
def test_individual_doc_pair_parity(root_rel, docs_rel):
    """Test individual file pair parity with precise error reporting."""
    root_path = os.path.join(REPO_ROOT, root_rel)
    docs_path = os.path.join(REPO_ROOT, docs_rel)

    assert os.path.exists(root_path), f"Canonical root doc missing: {root_rel}"
    assert os.path.exists(docs_path), f"Mirrored doc missing: {docs_rel}"

    with open(root_path, "r", encoding="utf-8") as f1, open(docs_path, "r", encoding="utf-8") as f2:
        c1 = f1.read()
        c2 = f2.read()

    assert c1 == c2, f"Content drift detected between {root_rel} and {docs_rel}"
