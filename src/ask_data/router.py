"""
Question router for Ask the Data module.

Routes natural language questions to SQL templates or LLM fallback.
Targets 70% coverage via templates to minimize LLM token usage.
"""

import re
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from .constants import ROUTER_PATTERNS, DEFAULT_WINDOW_DAYS


class QuestionRouter:
    """
    Routes natural language questions to SQL templates or LLM fallback.
    
    Uses regex patterns to match common question types and generate
    parameterized SQL queries. Falls back to LLM for unmatched questions.
    """
    
    def __init__(self):
        """Initialize router with compiled regex patterns."""
        self.patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> List[Tuple[re.Pattern, str, List[str], Optional[int], str]]:
        """Compile regex patterns for efficient matching."""
        compiled = []
        for pattern_str, view, columns, default_days, description in ROUTER_PATTERNS:
            pattern = re.compile(pattern_str, re.IGNORECASE)
            compiled.append((pattern, view, columns, default_days, description))
        return compiled
    
    def route(self, question: str) -> Dict[str, Any]:
        """
        Route a natural language question to appropriate handler.
        
        Args:
            question: Natural language question from user
            
        Returns:
            Dict with routing information and generated SQL if template matched
        """
        if not question or not question.strip():
            return {"routed": False, "error": "Empty question provided"}
        
        normalized = self._normalize_question(question)
        
        # Try template matching first
        template_result = self._match_template(normalized)
        if template_result:
            return {
                "routed": True,
                "type": "template",
                "sql": template_result["sql"],
                "view": template_result["view"],
                "days": template_result["days"],
                "description": template_result["description"],
                "columns": template_result["columns"]
            }
        
        # Fallback to LLM
        return {
            "routed": False,
            "type": "llm",
            "question": normalized
        }
    
    def _normalize_question(self, question: str) -> str:
        """
        Normalize question for consistent pattern matching.
        
        Args:
            question: Raw question text
            
        Returns:
            Normalized question string
        """
        # Convert to lowercase and remove extra whitespace
        normalized = " ".join(question.strip().lower().split())
        
        # Common abbreviations and variations (fixed logic)
        replacements = [
            ("rev", "revenue"),
            ("duplicate", "dup"),
            ("duplicates", "dup"),
            ("matching", "match"),
            ("customer", "customers"),
            ("order", "orders")
        ]
        
        for old, new in replacements:
            # Use word boundaries to avoid partial replacements
            normalized = re.sub(r'\b' + re.escape(old) + r'\b', new, normalized)
        
        return normalized
    
    def _match_template(self, question: str) -> Optional[Dict[str, Any]]:
        """
        Match question against known templates.
        
        Args:
            question: Normalized question text
            
        Returns:
            Template match result or None if no match
        """
        for pattern, view, columns, default_days, description in self.patterns:
            match = pattern.search(question)
            if match:
                # Extract days from pattern if present
                days = self._extract_days(question, match, default_days)
                
                # Generate SQL with proper partitioning
                sql = self._generate_sql(view, columns, days)
                
                return {
                    "sql": sql,
                    "view": view,
                    "days": days,
                    "description": description,
                    "columns": columns
                }
        
        return None
    
    def _extract_days(self, question: str, match: re.Match, default_days: Optional[int]) -> int:
        """
        Extract number of days from question or use default.
        
        Args:
            question: Original question text
            match: Regex match object
            default_days: Default days if not specified
            
        Returns:
            Number of days for query window
        """
        # Look for number followed by days/weeks/months
        time_patterns = [
            (r"(\d+)\s+days?", 1),
            (r"(\d+)\s+weeks?", 7),
            (r"(\d+)\s+months?", 30),
            (r"(\d+)\s+quarters?", 90),
            (r"\blast\s+quarter\b", 90),
            (r"\blast\s+qtr\b", 90),
        ]
        
        for pattern, multiplier in time_patterns:
            time_match = re.search(pattern, question, re.IGNORECASE)
            if time_match:
                if time_match.groups() and time_match.group(1):
                    return int(time_match.group(1)) * multiplier
                return multiplier
        
        # Use default or fallback to 90 days
        return default_days or DEFAULT_WINDOW_DAYS
    
    def _generate_sql(self, view: str, columns: List[str], days: int) -> str:
        """
        Generate parameterized SQL query with proper partitioning.
        
        Args:
            view: BigQuery view name
            columns: Columns to select
            days: Number of days for date window
            
        Returns:
            Generated SQL query string
        """
        # Determine date column based on view
        date_col = "date" if "metrics_" in view else "event_date"
        
        sql = f"""
        SELECT {', '.join(columns)}
        FROM `{view}`
        WHERE {date_col} >= DATE_SUB(CURRENT_DATE(), INTERVAL {days} DAY)
        ORDER BY {date_col}
        LIMIT 50000
        """.strip()
        
        return sql
    
    def get_coverage_stats(self) -> Dict[str, Any]:
        """
        Get router coverage statistics.
        
        Returns:
            Dict with pattern count and coverage information
        """
        return {
            "total_patterns": len(self.patterns),
            "views_covered": list(set(pattern[1] for pattern in self.patterns)),
            "description": "Router covers common business questions with SQL templates"
        }
