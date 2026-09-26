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

import functools
import sys

FALLBACK_PACKAGE_VERSION = "0.7.1"
FALLBACK_MODEL_VERSION = "v1.6 Ipatieff"


@functools.lru_cache(maxsize=1)
def _read_pyproject_version() -> Optional[str]:
    """Reads the project version from pyproject.toml."""
    try:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        pyproject_path = os.path.join(repo_root, "pyproject.toml")
        if os.path.exists(pyproject_path):
            if sys.version_info >= (3, 11):
                import tomllib
                with open(pyproject_path, "rb") as f:
                    data = tomllib.load(f)
                    return data.get("project", {}).get("version", "").lstrip("v")
            else:
                with open(pyproject_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip().startswith("version"):
                            m = re.search(r'version\s*=\s*"([^"]+)"', line)
                            if m:
                                return m.group(1).lstrip("v")
    except Exception as e:
        logger.debug(f"Failed reading pyproject.toml version: {e}")
    return None


def get_version() -> str:
    """
    Resolves current Midgley package version from:
    1. MIDGLEY_VERSION environment variable override.
    2. pyproject.toml project.version (single source of truth).
    3. Fallback package version ('0.7.0').
    """
    env_ver = os.getenv("MIDGLEY_VERSION", "").strip()
    if env_ver:
        return env_ver.lstrip("v")

    pyproject_ver = _read_pyproject_version()
    if pyproject_ver:
        return pyproject_ver

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
