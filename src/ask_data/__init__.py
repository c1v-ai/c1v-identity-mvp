"""
Ask the Data - C1V Module

Natural language to SQL query interface with router-first approach.
Reuses existing C1V infrastructure for identity and data processing.
"""

__version__ = "0.1.0"
__author__ = "C1V Team"

from .router import QuestionRouter
from .constants import DEFAULT_WINDOW_DAYS, DRY_RUN_MAX_BYTES, ROW_CAP

__all__ = [
    "QuestionRouter",
    "DEFAULT_WINDOW_DAYS",
    "DRY_RUN_MAX_BYTES", 
    "ROW_CAP"
]
