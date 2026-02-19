"""Offerman exceptions."""

from typing import Any


ERROR_MESSAGES = {
    "SKU_NOT_FOUND": "SKU not found",
    "SKU_INACTIVE": "SKU is inactive",
    "NOT_A_BUNDLE": "SKU is not a bundle",
    "INVALID_PRICE_LIST": "Invalid price list",
    "PRICE_LIST_EXPIRED": "Price list expired",
    "INVALID_QUANTITY": "Invalid quantity",
    "CIRCULAR_COMPONENT": "Circular component reference detected",
}


class CatalogError(Exception):
    """
    Structured exception for catalog operations.

    Usage:
        try:
            price = catalog.price("XYZ")
        except CatalogError as e:
            if e.code == "SKU_NOT_FOUND":
                print(f"SKU {e.sku} does not exist")
    """

    def __init__(self, code: str, message: str = "", **data: Any) -> None:
        self.code = code
        self.message = message or ERROR_MESSAGES.get(code, code)
        self.data = data
        super().__init__(f"[{code}] {self.message}")

    @property
    def sku(self) -> str | None:
        return self.data.get("sku")

    def as_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "data": self.data,
        }
