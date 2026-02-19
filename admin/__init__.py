"""Offerman admin."""

from offerman.admin.collection import CollectionAdmin, CollectionItemInline
from offerman.admin.listing import ListingAdmin, ListingItemInline
from offerman.admin.product import ProductAdmin

__all__ = [
    "CollectionAdmin",
    "CollectionItemInline",
    "ListingAdmin",
    "ListingItemInline",
    "ProductAdmin",
]
