"""
Alternative product suggestions.

When a product is unavailable, suggests similar products
based on keywords, collection, and other criteria.
"""

from offerman.models import Product
from offerman.service import CatalogService


def _get_primary_collection(product: Product):
    """Get the primary collection for a product."""
    primary_item = product.collection_items.filter(is_primary=True).first()
    return primary_item.collection if primary_item else None


def find_alternatives(
    sku: str,
    limit: int = 5,
    same_collection: bool = True,
) -> list[Product]:
    """
    Find alternatives for a product.

    Algorithm:
    1. Find products with common keywords
    2. Prioritize same collection (if same_collection=True)
    3. Sort by number of common keywords

    Args:
        sku: SKU of unavailable product
        limit: Maximum suggestions
        same_collection: Prioritize same primary collection

    Returns:
        List of alternative products
    """
    product = CatalogService.get(sku)
    if not product:
        return []

    product_keywords = list(product.keywords.names())
    if not product_keywords:
        return []

    qs = (
        Product.objects.filter(
            is_published=True,
            is_available=True,
            keywords__name__in=product_keywords,
        )
        .exclude(sku=sku)
        .distinct()
    )

    if same_collection:
        primary_collection = _get_primary_collection(product)
        if primary_collection:
            # Filter by products in the same collection
            qs = qs.filter(collection_items__collection=primary_collection)

    # TODO: Sort by number of common keywords
    # Requires annotate with Count conditional or raw SQL

    return list(qs[:limit])


def find_similar(
    sku: str,
    limit: int = 5,
) -> list[Product]:
    """
    Find similar products (same concept, variations).

    Useful for: "You might also like..."

    Args:
        sku: Reference SKU
        limit: Maximum suggestions

    Returns:
        List of similar products
    """
    product = CatalogService.get(sku)
    if not product:
        return []

    # Get primary collection
    primary_collection = _get_primary_collection(product)

    # Same collection + at least one common keyword
    qs = (
        Product.objects.filter(
            is_published=True,
            is_available=True,
        )
        .exclude(sku=sku)
    )

    if primary_collection:
        qs = qs.filter(collection_items__collection=primary_collection)

    product_keywords = list(product.keywords.names())
    if product_keywords:
        qs = qs.filter(keywords__name__in=product_keywords).distinct()

    return list(qs[:limit])
