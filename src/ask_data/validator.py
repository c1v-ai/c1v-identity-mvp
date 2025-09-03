"""
SQL validation and guardrails for Ask the Data module.

Ensures queries are safe, performant, and comply with security policies.
"""

import re
from typing import Tuple, List, Set, Optional
from .constants import ALLOWED_VIEWS, DRY_RUN_MAX_BYTES, ROW_CAP, ERROR_MESSAGES


class SQLValidator:
    """
    Validates SQL queries and enforces guardrails.
    
    Ensures:
    - No DML operations
    - No SELECT *
    - Only allowed views
    - Date partitioning required
    - Row limits enforced
    """
    
    def __init__(self):
        """Initialize validator with configuration."""
        self.allowed_views = ALLOWED_VIEWS
        self.max_bytes = DRY_RUN_MAX_BYTES
        self.row_cap = ROW_CAP
    
    def validate_and_sanitize(self, sql: str) -> Tuple[bool, str]:
        """
        Validate SQL and apply sanitization rules.
        
        Args:
            sql: Raw SQL query string
            
        Returns:
            Tuple of (is_valid, sanitized_sql_or_error_message)
        """
        # Normalize SQL
        normalized_sql = self._normalize_sql(sql)
        
        # Check for DML operations
        if self._contains_dml(normalized_sql):
            return False, ERROR_MESSAGES["dml_not_allowed"]
        
        # Check for SELECT *
        if self._contains_select_star(normalized_sql):
            return False, ERROR_MESSAGES["select_star_not_allowed"]
        
        # Check view allowlist
        if not self._views_allowed(normalized_sql):
            return False, ERROR_MESSAGES["view_not_allowed"]
        
        # Ensure date partitioning
        sanitized_sql = self._ensure_date_partition(normalized_sql)
        
        # Ensure row limits
        sanitized_sql = self._ensure_row_limits(sanitized_sql)
        
        return True, sanitized_sql
    
    def _normalize_sql(self, sql: str) -> str:
        """Normalize SQL for consistent validation."""
        # Remove comments and normalize whitespace
        sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)  # Remove single-line comments
        sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)  # Remove multi-line comments
        sql = " ".join(sql.split())  # Normalize whitespace
        return sql
    
    def _contains_dml(self, sql: str) -> bool:
        """Check if SQL contains DML operations."""
        dml_patterns = [
            r'\binsert\b',
            r'\bupdate\b', 
            r'\bdelete\b',
            r'\bmerge\b',
            r'\bdrop\b',
            r'\balter\b',
            r'\bcreate\b',
            r'\btruncate\b'
        ]
        
        for pattern in dml_patterns:
            if re.search(pattern, sql, re.IGNORECASE):
                return True
        return False
    
    def _contains_select_star(self, sql: str) -> bool:
        """Check if SQL contains SELECT * (not COUNT(*) etc.)."""
        # Detect 'SELECT * FROM' anywhere (avoids matching COUNT(*))
        return bool(re.search(r'(?i)\bselect\s*\*[\s\r\n]*from\b', sql))
    
    def _views_allowed(self, sql: str) -> bool:
        """Check if all referenced views are in allowlist."""
        # Extract table/view names from FROM and JOIN clauses
        table_pattern = r'(?:from|join)\s+`?([a-z0-9_.]+)`?'
        tables = re.findall(table_pattern, sql, re.IGNORECASE)
        
        if not tables:
            return False
        
        # Check if all tables are allowed
        for table in tables:
            if table not in self.allowed_views:
                return False
        
        return True
    
    def _ensure_date_partition(self, sql: str) -> str:
        """Ensure SQL has date partitioning for performance."""
        # Check if date partitioning is already present
        date_patterns = [
            r'\bdate\s*>=\s*date_',
            r'\bevent_date\s*>=\s*date_',
            r'\bcreated_at\s*>=\s*date_'
        ]
        
        has_date_partition = any(re.search(pattern, sql, re.IGNORECASE) for pattern in date_patterns)
        
        if not has_date_partition:
            # Add default date partitioning
            # Find the appropriate date column based on views used
            if 'metrics_' in sql:
                date_col = 'date'
            else:
                date_col = 'event_date'
            
            # Insert WHERE clause before ORDER BY or LIMIT
            if 'ORDER BY' in sql.upper():
                sql = re.sub(r'\bORDER BY\b', f'WHERE {date_col} >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY) ORDER BY', sql, flags=re.IGNORECASE)
            elif 'LIMIT' in sql.upper():
                sql = re.sub(r'\bLIMIT\b', f'WHERE {date_col} >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY) LIMIT', sql, flags=re.IGNORECASE)
            else:
                sql += f' WHERE {date_col} >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)'
        
        return sql
    
    def _ensure_row_limits(self, sql: str) -> str:
        """Ensure SQL has row limits."""
        if not re.search(r'\blimit\b', sql, re.IGNORECASE):
            sql += f' LIMIT {self.row_cap}'
        
        return sql
    
    def validate_query_structure(self, sql: str) -> List[str]:
        """
        Validate SQL structure and return warnings/errors.
        
        Args:
            sql: SQL query to validate
            
        Returns:
            List of validation messages
        """
        messages = []
        
        # Check for common issues
        if 'GROUP BY' in sql.upper() and 'HAVING' not in sql.upper():
            messages.append("Consider adding HAVING clause for GROUP BY queries")
        
        if 'ORDER BY' in sql.upper() and 'LIMIT' not in sql.upper():
            messages.append("Consider adding LIMIT for ORDER BY queries")
        
        if sql.count('JOIN') > 2:
            messages.append("Multiple JOINs may impact performance")
        
        return messages


# Convenience function for quick validation
def validate_sql(sql: str) -> Tuple[bool, str]:
    """
    Quick SQL validation function.
    
    Args:
        sql: SQL query string
        
    Returns:
        Tuple of (is_valid, result_or_error)
    """
    validator = SQLValidator()
    return validator.validate_and_sanitize(sql)
