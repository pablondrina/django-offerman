"""
Offerman public API.

CORE (essential):
    CatalogService.get(sku)      - Get product
    CatalogService.price(sku)    - Get price
    CatalogService.expand(sku)   - Expand bundle into components
    CatalogService.validate(sku) - Validate SKU

CONVENIENCE (helpers):
    CatalogService.search(...)   - Search products

LISTING / CHANNEL (per-channel availability):
    CatalogService.get_available_products(listing_code) - Products available in listing
    CatalogService.is_product_available(product, listing_code) - Check availability
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING

from django.db import models

from offerman.exceptions import CatalogError

if TYPE_CHECKING:
    from offerman.models import Product
    from offerman.protocols import SkuValidation


class CatalogService:
    """
    Offerman public API.

    Uses @classmethod for extensibility (see spec 000 section 12.1).

    CORE (essential):
        get(sku)      - Get product
        price(sku)    - Get price (base_price or via pricing backend)
        expand(sku)   - Expand bundle into components
        validate(sku) - Validate SKU

    CONVENIENCE (helpers):
        search(...)   - Search products
    """

    # ======================================================================
    # CORE API
    # ======================================================================

    @classmethod
    def get(cls, sku: str | list[str]) -> "Product | dict[str, Product] | None":
        """
        Get product(s) by SKU.

        Args:
            sku: Single SKU or list of SKUs

        Returns:
            Product | None (for single SKU)
            dict[sku, Product] (for list)
        """
        from offerman.models import Product

        if isinstance(sku, list):
            products = Product.objects.filter(sku__in=sku)
            return {p.sku: p for p in products}
        return cls._fetch_product(sku)

    @classmethod
    def _fetch_product(cls, sku: str) -> "Product | None":
        """Internal: fetch product by SKU. Override for caching, etc."""
        from offerman.models import Product

        return Product.objects.filter(sku=sku).first()

    @classmethod
    def price(
        cls,
        sku: str,
        qty: Decimal = Decimal("1"),
        channel: str | None = None,
        price_list: str | None = None,
    ) -> int:
        """
        Return total price in cents.

        CORE: Uses base_price_q from product.
        With contrib.price_lists: Supports channel→price_list lookup.

        Args:
            sku: Product code
            qty: Quantity
            channel: Channel slug (convention: looks for PriceList with same code)
            price_list: Price list code (override)

        Returns:
            Total price in cents (unit_price * qty)

        Raises:
            CatalogError: If SKU not found
        """
        if qty <= 0:
            raise CatalogError("INVALID_QUANTITY", sku=sku, qty=str(qty))

        product = cls.get(sku)
        if not product:
            raise CatalogError("SKU_NOT_FOUND", sku=sku)

        # If price_lists contrib installed, try specific list
        effective_price_list = price_list or channel
        if effective_price_list:
            unit_price = cls._get_price_from_list(product, effective_price_list, qty)
            if unit_price is not None:
                return int(Decimal(str(unit_price * qty)).to_integral_value(rounding=ROUND_HALF_UP))

        # Fallback: base price
        return int(Decimal(str(product.base_price_q * qty)).to_integral_value(rounding=ROUND_HALF_UP))

    @classmethod
    def _get_price_from_list(
        cls,
        product: "Product",
        price_list_code: str,
        qty: Decimal,
    ) -> int | None:
        """
        Get price from specific price list.

        Override in contrib.price_lists for real implementation.
        Core returns None (fallback to base_price).
        """
        # Try to use PriceList if available (contrib)
        try:
            from offerman.models import PriceList, PriceListItem

            pl = PriceList.objects.filter(code=price_list_code).first()
            if not pl or not pl.is_valid():
                return None

            # Find item with highest min_qty that is still <= qty.
            # Only return price for published and available items in this channel.
            item = (
                PriceListItem.objects.filter(
                    listing=pl,
                    product=product,
                    min_qty__lte=qty,
                    is_published=True,
                    is_available=True,
                )
                .order_by("-min_qty")
                .first()
            )

            return item.price_q if item else None

        except (ImportError, LookupError, ValueError):
            # PriceList not available or not found
            return None

    @classmethod
    def expand(cls, sku: str, qty: Decimal = Decimal("1")) -> list[dict]:
        """
        Expand bundle into components.

        Args:
            sku: Bundle SKU
            qty: Bundle quantity

        Returns:
            List of components:
            [{"sku": "X", "name": "...", "qty": Decimal}, ...]

        Raises:
            CatalogError: If not a bundle
        """
        product = cls.get(sku)
        if not product:
            raise CatalogError("SKU_NOT_FOUND", sku=sku)

        if not product.is_bundle:
            raise CatalogError("NOT_A_BUNDLE", sku=sku)

        return [
            {
                "sku": comp.component.sku,
                "name": comp.component.name,
                "qty": comp.qty * qty,
            }
            for comp in product.components.select_related("component")
        ]

    @classmethod
    def validate(cls, sku: str) -> "SkuValidation":
        """
        Validate SKU and return structured information.

        Returns:
            SkuValidation dataclass
        """
        from offerman.protocols import SkuValidation

        product = cls.get(sku)

        if not product:
            return SkuValidation(
                valid=False,
                sku=sku,
                error_code="not_found",
                message=f"SKU '{sku}' not found",
            )

        return SkuValidation(
            valid=True,
            sku=sku,
            name=product.name,
            is_published=product.is_published,
            is_available=product.is_available,
            message=cls._get_validation_message(product),
        )

    @classmethod
    def _get_validation_message(cls, product: "Product") -> str | None:
        """Generate validation message based on product state."""
        if not product.is_published:
            return "Product is not published in catalog"
        if not product.is_available:
            return "Product is not available for purchase"
        return None

    # ======================================================================
    # CONVENIENCE API
    # ======================================================================

    @classmethod
    def search(
        cls,
        query: str | None = None,
        collection: str | None = None,
        keywords: list[str] | None = None,
        only_published: bool = True,
        only_available: bool = True,
        limit: int = 20,
    ) -> list["Product"]:
        """
        Search products.

        Args:
            query: Search term (name, SKU or keywords)
            collection: Filter by collection (slug)
            keywords: Filter by keywords - requires django-taggit
            only_published: Only published (is_published=True)
            only_available: Only available (is_available=True)
            limit: Maximum results

        Returns:
            List of Product
        """
        from offerman.models import Product

        qs = Product.objects.all()

        if only_published:
            qs = qs.filter(is_published=True)
        if only_available:
            qs = qs.filter(is_available=True)
        if query:
            qs = qs.filter(
                models.Q(sku__icontains=query) | models.Q(name__icontains=query)
            ).distinct()

        # Collection filter
        if collection:
            qs = qs.filter(collection_items__collection__slug=collection)
        if keywords:
            qs = qs.filter(keywords__name__in=keywords).distinct()

        return list(qs[:limit])

    # ======================================================================
    # LISTING / CHANNEL API
    # ======================================================================

    @classmethod
    def get_available_products(cls, listing_code: str) -> models.QuerySet["Product"]:
        """
        Products available in a listing.

        A product is available if:
        - Product.is_published = True (global)
        - Product.is_available = True (global)
        - Listing.is_active = True
        - ListingItem.is_published = True (per-channel)
        - ListingItem.is_available = True (per-channel)

        Args:
            listing_code: Listing code (convention: same as Channel.code)

        Returns:
            QuerySet of available products
        """
        from offerman.models import Product

        return Product.objects.filter(
            is_published=True,
            is_available=True,
            listing_items__listing__code=listing_code,
            listing_items__listing__is_active=True,
            listing_items__is_published=True,
            listing_items__is_available=True,
        ).distinct()

    @classmethod
    def is_product_available(cls, product: "Product", listing_code: str) -> bool:
        """
        Check if product is available in listing.

        Args:
            product: Product instance
            listing_code: Listing code

        Returns:
            True if product is available in the listing
        """
        if not product.is_published or not product.is_available:
            return False

        from offerman.models import ListingItem

        return ListingItem.objects.filter(
            listing__code=listing_code,
            listing__is_active=True,
            product=product,
            is_published=True,
            is_available=True,
        ).exists()
