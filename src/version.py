"""
Dynamic Versioning & Model Badging Engine (src/version.py)
Provides unified, self-healing dynamic version, model engine, and git branch resolution
across the public web dashboard, REST API server, and CI/CD automation pipelines (Issue #298).
"""

import os
import re
import glob
import subprocess
import logging
from typing import Optional

logger = logging.getLogger(__name__)

FALLBACK_PACKAGE_VERSION = "0.6.8"
FALLBACK_MODEL_VERSION = "v1.6 Ipatieff"


def get_version() -> str:
    """
    Dynamically resolves the current Midgley package version using a 5-tier fallback chain:
    1. MIDGLEY_VERSION environment variable.
    2. Latest git release tag (e.g. 'v0.6.8' -> '0.6.8') via git describe/tags.
    3. Highest semver version from RELEASE_NOTES_v*.md files in repository root.
    4. pyproject.toml package version.
    5. Immutable fallback constant ('0.6.8').
    """
    # Tier 1: Explicit environment variable
    env_ver = os.getenv("MIDGLEY_VERSION", "").strip()
    if env_ver:
        return env_ver.lstrip("v")

    # Collect candidate versions across discovery tiers
    candidates = []

    # Tier 2: Git describe / tag resolution
    try:
        cmd_out = subprocess.check_output(
            ["git", "describe", "--tags", "--abbrev=0"],
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
        if cmd_out:
            clean_ver = cmd_out.lstrip("v").strip()
            if re.match(r"^\d+\.\d+(\.\d+)?", clean_ver):
                candidates.append(clean_ver)
    except Exception:
        pass

    # Tier 2b: Git tag list sorting
    try:
        cmd_out = subprocess.check_output(
            ["git", "tag", "-l", "v*"],
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
        if cmd_out:
            tag_lines = [t.strip().lstrip("v") for t in cmd_out.splitlines() if t.strip()]
            valid_tags = [t for t in tag_lines if re.match(r"^\d+\.\d+(\.\d+)?", t)]
            if valid_tags:
                candidates.extend(valid_tags)
    except Exception:
        pass

    # Tier 3: Scan RELEASE_NOTES_v*.md files
    try:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        rel_files = glob.glob(os.path.join(repo_root, "RELEASE_NOTES_v*.md"))
        for rf in rel_files:
            fname = os.path.basename(rf)
            m = re.search(r"RELEASE_NOTES_v(\d+\.\d+(\.\d+)?)\.md", fname)
            if m:
                candidates.append(m.group(1))
    except Exception:
        pass

    # Tier 4: pyproject.toml
    try:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        pyproject_path = os.path.join(repo_root, "pyproject.toml")
        if os.path.exists(pyproject_path):
            with open(pyproject_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("version"):
                        m = re.search(r'version\s*=\s*"([^"]+)"', line)
                        if m:
                            candidates.append(m.group(1).lstrip("v"))
    except Exception:
        pass

    # Tier 5: Fallback constant
    candidates.append(FALLBACK_PACKAGE_VERSION)

    # Return highest semver candidate
    clean_candidates = [c for c in candidates if re.match(r"^\d+\.\d+(\.\d+)?", c)]
    if clean_candidates:
        clean_candidates.sort(key=lambda s: [int(u) for u in s.split(".") if u.isdigit()])
        return clean_candidates[-1]

    return FALLBACK_PACKAGE_VERSION


def get_model_version() -> str:
    """
    Dynamically resolves the active quantitative model engine version string:
    1. MIDGLEY_MODEL_VERSION environment variable.
    2. src.__model_version__ package constant.
    3. Fallback constant ('v1.6 Ipatieff').
    """
    env_model = os.getenv("MIDGLEY_MODEL_VERSION", "").strip()
    if env_model:
        return env_model

    try:
        from src import __model_version__
        if __model_version__:
            return __model_version__
    except Exception:
        pass

    return FALLBACK_MODEL_VERSION


get_model_engine_version = get_model_version


def get_git_branch() -> str:
    """
    Dynamically resolves the active git branch or deployment environment context.
    """
    # Explicit env overrides
    env_branch = os.getenv("MIDGLEY_BRANCH", "").strip()
    if env_branch:
        return env_branch

    ref_name = os.getenv("GITHUB_REF_NAME", "").strip()
    if ref_name:
        return ref_name

    head_ref = os.getenv("GITHUB_HEAD_REF", "").strip()
    if head_ref:
        return head_ref

    # Git CLI detection
    try:
        cmd_out = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
        if cmd_out and cmd_out != "HEAD":
            return cmd_out
    except Exception:
        pass

    # In CI release or deployment environment, default to main if pages/production
    if os.getenv("GITHUB_ACTIONS") and os.getenv("GITHUB_EVENT_NAME") in ["schedule", "workflow_dispatch"]:
        return "main"

    return "dev"


def is_release_branch() -> bool:
    """Returns True if the current branch is main/master or a release branch."""
    branch = get_git_branch()
    return branch in ["main", "master"] or branch.startswith("release/")


if __name__ == "__main__":
    print(f"Package Version: {get_version()}")
    print(f"Model Engine Version: {get_model_version()}")
    print(f"Git Branch: {get_git_branch()} (Is Release: {is_release_branch()})")
