"""
Noop CostBackend -- default for projects that don't need cost tracking.

This adapter implements the CostBackend protocol and always returns None,
meaning no production cost is known for any product. Product.reference_cost_q
and Product.margin_percent will both return None.

Usage in settings.py:
    OFFERMAN = {
        "COST_BACKEND": "offerman.adapters.noop.NoopCostBackend",
    }

This is equivalent to leaving COST_BACKEND unset (None), but makes the
intent explicit in configuration.
"""

from __future__ import annotations

from offerman.protocols.cost import CostBackend


class NoopCostBackend:
    """
    CostBackend that returns None for every SKU.

    Use this when your project does not track production costs.
    Offerman will behave as if no cost data exists: margin
    calculations will return None and no errors will be raised.
    """

    def get_cost(self, sku: str) -> int | None:
        """Always returns None -- no cost tracking."""
        return None


# Verify protocol compliance at import time.
if not isinstance(NoopCostBackend(), CostBackend):
    raise TypeError("NoopCostBackend does not implement CostBackend protocol")
