"""
Suggestions module - find alternative products.

Usage:
    from offerman.contrib.suggestions import find_alternatives, find_similar

    alternatives = find_alternatives("SKU-001")
    similar = find_similar("SKU-001")
"""

from offerman.contrib.suggestions.suggestions import find_alternatives, find_similar

__all__ = ["find_alternatives", "find_similar"]
