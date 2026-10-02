"""Slow-query log helper for the customer support console.

Support engineers paste SQL snippets reported by customers into the
console's search box; this module normalizes them before log lookup.
"""
import sqlparse

KEYWORD_CASE = "upper"


def normalize_query(raw_query: str) -> str:
    """Normalize a pasted SQL snippet for log lookup."""
    formatted = sqlparse.format(
        raw_query,
        keyword_case=KEYWORD_CASE,
        strip_comments=True,
        reindent=True,
    )
    return formatted.strip()
