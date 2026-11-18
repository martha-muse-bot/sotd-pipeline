"""
Strategy Utilities

This module contains utility functions and classes for brush matching strategies.
"""

# Import utility functions
from .pattern_utils import *  # noqa: F403, F405

# No module-level __all__: the names the old one listed (compile_pattern,
# match_pattern, extract_pattern_groups, ...) never existed in pattern_utils,
# and all real consumers import the submodules directly.
