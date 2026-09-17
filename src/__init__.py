"""
Gas Price LLM Prediction Package (midgley)
Package Version: 0.6.1
Model Engine Version: v1.6 Ipatieff
"""

from src.version import get_version, get_model_version, get_git_branch, is_release_branch

__version__ = get_version()
__model_version__ = get_model_version()

__all__ = [
    "__version__",
    "__model_version__",
    "get_version",
    "get_model_version",
    "get_git_branch",
    "is_release_branch"
]
