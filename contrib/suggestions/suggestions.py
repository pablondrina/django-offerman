"""
Alternative product suggestions with scoring.

When a product is unavailable, suggests similar products
based on keywords, collection, and price similarity.

Scoring weights:
    - Keywords in common: 3 points each
    - Same collection: 2 points
    - Price within ±30%: 1 point
"""

from decimal import Decimal

from offerman.models import Product
from offerman.service import CatalogService


def _get_primary_collection(product: Product):
    """Get the primary collection for a product."""
    primary_item = product.collection_items.filter(is_primary=True).first()
    return primary_item.collection if primary_item else None


def _score_candidates(
    candidates: list[Product],
    product: Product,
    product_keywords: list[str],
    primary_collection,
) -> list[Product]:
    """
    Score and sort candidate products.

    Scoring:
        - Keywords in common: 3 points each
        - Same collection as reference: 2 points
        - Price within ±30% of reference: 1 point
    """
    price_low = int(product.base_price_q * Decimal("0.7"))
    price_high = int(product.base_price_q * Decimal("1.3"))

    # Prefetch keywords and collections for candidates
    collection_product_ids = set()
    if primary_collection:
        collection_product_ids = set(
            primary_collection.items.values_list("product_id", flat=True)
        )

    scored = []
    for candidate in candidates:
        score = 0

        # Keywords in common (3 points each)
        candidate_keywords = set(candidate.keywords.names())
        common = len(set(product_keywords) & candidate_keywords)
        score += common * 3

        # Same collection (2 points)
        if primary_collection and candidate.pk in collection_product_ids:
            score += 2

        # Price within ±30% (1 point)
        if price_low <= candidate.base_price_q <= price_high:
            score += 1

        scored.append((score, candidate))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [candidate for _, candidate in scored]


def find_alternatives(
    sku: str,
    limit: int = 5,
    same_collection: bool = True,
) -> list[Product]:
    """
    Find alternatives for a product.

    Algorithm:
    1. Find products with common keywords
    2. Optionally filter by same collection
    3. Score by keywords (x3), collection (x2), price similarity (x1)

    Args:
        sku: SKU of unavailable product
        limit: Maximum suggestions
        same_collection: Prioritize same primary collection

    Returns:
        List of alternative products, sorted by score descending
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

    primary_collection = _get_primary_collection(product)

    if same_collection and primary_collection:
        qs = qs.filter(collection_items__collection=primary_collection)

    # Fetch a wider pool for scoring, then trim
    candidates = list(qs[: limit * 3])
    scored = _score_candidates(candidates, product, product_keywords, primary_collection)
    return scored[:limit]


def find_similar(
    sku: str,
    limit: int = 5,
) -> list[Product]:
    """
    Find similar products (same concept, variations).

    Useful for: "You might also like..."

    Uses full scoring: keywords in common (x3), same collection (x2),
    price similarity (x1).

    Args:
        sku: Reference SKU
        limit: Maximum suggestions

    Returns:
        List of similar products, sorted by score descending
    """
    product = CatalogService.get(sku)
    if not product:
        return []

    primary_collection = _get_primary_collection(product)
    product_keywords = list(product.keywords.names())

    qs = (
        Product.objects.filter(
            is_published=True,
            is_available=True,
        )
        .exclude(sku=sku)
    )

    if primary_collection:
        qs = qs.filter(collection_items__collection=primary_collection)

    if product_keywords:
        qs = qs.filter(keywords__name__in=product_keywords).distinct()

    candidates = list(qs[: limit * 3])
    scored = _score_candidates(candidates, product, product_keywords, primary_collection)
    return scored[:limit]
