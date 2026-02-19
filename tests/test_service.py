"""Tests for Offerman service (CatalogService API)."""

from decimal import Decimal

import pytest

from offerman.service import CatalogService
from offerman.exceptions import CatalogError
from offerman.models import Product, Listing, ListingItem


pytestmark = pytest.mark.django_db


class TestCatalogGet:
    """Tests for CatalogService.get()."""

    def test_get_single_product(self, db):
        """Test getting single product by SKU."""
        product = Product.objects.create(sku="BAGUETE", name="Baguete")
        result = CatalogService.get("BAGUETE")
        assert result == product

    def test_get_nonexistent(self, db):
        """Test getting nonexistent product."""
        result = CatalogService.get("NONEXISTENT")
        assert result is None

    def test_get_multiple_products(self, db):
        """Test getting multiple products."""
        product = Product.objects.create(sku="BAGUETE", name="Baguete")
        croissant = Product.objects.create(sku="CROISSANT", name="Croissant")

        result = CatalogService.get(["BAGUETE", "CROISSANT"])
        assert len(result) == 2
        assert result["BAGUETE"] == product
        assert result["CROISSANT"] == croissant

    def test_get_multiple_partial(self, db):
        """Test getting multiple with some missing."""
        Product.objects.create(sku="BAGUETE", name="Baguete")

        result = CatalogService.get(["BAGUETE", "NONEXISTENT"])
        assert len(result) == 1
        assert "BAGUETE" in result


class TestCatalogPrice:
    """Tests for CatalogService.price()."""

    def test_price_base(self, db):
        """Test base price."""
        Product.objects.create(sku="BAGUETE", name="Baguete", base_price_q=500)
        price = CatalogService.price("BAGUETE")
        assert price == 500  # R$ 5.00 in cents

    def test_price_with_quantity(self, db):
        """Test price with quantity."""
        Product.objects.create(sku="BAGUETE", name="Baguete", base_price_q=500)
        price = CatalogService.price("BAGUETE", qty=Decimal("3"))
        assert price == 1500  # 3 x R$ 5.00

    def test_price_from_listing(self, db):
        """Test price from listing."""
        product = Product.objects.create(sku="BAGUETE", name="Baguete", base_price_q=500)
        listing = Listing.objects.create(code="ifood", name="iFood")
        ListingItem.objects.create(listing=listing, product=product, price_q=600)

        price = CatalogService.price("BAGUETE", channel="ifood")
        assert price == 600  # R$ 6.00 from iFood listing

    def test_price_fallback_to_base(self, db):
        """Test fallback to base price when no listing."""
        Product.objects.create(sku="BAGUETE", name="Baguete", base_price_q=500)
        price = CatalogService.price("BAGUETE", channel="nonexistent")
        assert price == 500  # Fallback to base

    def test_price_nonexistent_product(self, db):
        """Test price for nonexistent product."""
        with pytest.raises(CatalogError) as exc:
            CatalogService.price("NONEXISTENT")
        assert exc.value.code == "SKU_NOT_FOUND"


class TestCatalogExpand:
    """Tests for CatalogService.expand()."""

    def test_expand_bundle(self, db):
        """Test expanding bundle."""
        from offerman.models import ProductComponent

        combo = Product.objects.create(sku="COMBO-CAFE", name="Combo Café")
        croissant = Product.objects.create(sku="CROISSANT", name="Croissant")
        coffee = Product.objects.create(sku="COFFEE", name="Coffee")

        ProductComponent.objects.create(parent=combo, component=croissant, qty=Decimal("1"))
        ProductComponent.objects.create(parent=combo, component=coffee, qty=Decimal("1"))

        components = CatalogService.expand("COMBO-CAFE")
        assert len(components) == 2

        skus = [c["sku"] for c in components]
        assert "CROISSANT" in skus
        assert "COFFEE" in skus

    def test_expand_non_bundle(self, db):
        """Test expanding non-bundle product."""
        Product.objects.create(sku="BAGUETE", name="Baguete")

        with pytest.raises(CatalogError) as exc:
            CatalogService.expand("BAGUETE")
        assert exc.value.code == "NOT_A_BUNDLE"

    def test_expand_nonexistent(self, db):
        """Test expanding nonexistent product."""
        with pytest.raises(CatalogError) as exc:
            CatalogService.expand("NONEXISTENT")
        assert exc.value.code == "SKU_NOT_FOUND"


class TestCatalogValidate:
    """Tests for CatalogService.validate()."""

    def test_validate_valid_product(self, db):
        """Test validating valid product."""
        Product.objects.create(sku="BAGUETE", name="Baguete Tradicional")

        result = CatalogService.validate("BAGUETE")
        assert result.valid is True
        assert result.sku == "BAGUETE"
        assert result.name == "Baguete Tradicional"
        assert result.is_published is True
        assert result.is_available is True
        assert result.message is None

    def test_validate_unpublished_product(self, db):
        """Test validating unpublished product."""
        Product.objects.create(sku="HIDDEN-001", name="Hidden", is_published=False)

        result = CatalogService.validate("HIDDEN-001")
        assert result.valid is True
        assert result.is_published is False
        assert "not published" in result.message.lower()

    def test_validate_nonexistent(self, db):
        """Test validating nonexistent product."""
        result = CatalogService.validate("NONEXISTENT")
        assert result.valid is False
        assert result.error_code == "not_found"


class TestCatalogSearch:
    """Tests for CatalogService.search()."""

    def test_search_by_name(self, db):
        """Test search by name."""
        product = Product.objects.create(sku="BAGUETE", name="Baguete")
        Product.objects.create(sku="CROISSANT", name="Croissant")

        results = CatalogService.search(query="Baguete")
        assert len(results) == 1
        assert results[0] == product

    def test_search_by_sku(self, db):
        """Test search by SKU."""
        product = Product.objects.create(sku="BAGUETE", name="Baguete")

        results = CatalogService.search(query="BAGUETE")
        assert len(results) == 1
        assert results[0] == product

    def test_search_excludes_unpublished(self, db):
        """Test search excludes unpublished by default."""
        Product.objects.create(sku="BAGUETE", name="Baguete")
        Product.objects.create(sku="HIDDEN-001", name="Hidden", is_published=False)

        results = CatalogService.search(only_published=True)
        skus = [p.sku for p in results]
        assert "BAGUETE" in skus
        assert "HIDDEN-001" not in skus

    def test_search_limit(self, db):
        """Test search limit."""
        for i in range(10):
            Product.objects.create(
                sku=f"TEST-{i:03d}",
                name=f"Test Product {i}",
                base_price_q=100,
            )

        results = CatalogService.search(limit=5)
        assert len(results) <= 5


class TestCatalogAvailability:
    """Tests for CatalogService availability methods."""

    def test_get_available_products(self, db):
        """Test getting available products for a listing."""
        listing = Listing.objects.create(code="shop", name="Shop")
        product1 = Product.objects.create(sku="P1", name="Product 1")
        product2 = Product.objects.create(sku="P2", name="Product 2", is_available=False)

        ListingItem.objects.create(listing=listing, product=product1, price_q=500)
        ListingItem.objects.create(listing=listing, product=product2, price_q=600)

        available = CatalogService.get_available_products("shop")
        skus = [p.sku for p in available]
        assert "P1" in skus
        assert "P2" not in skus  # Not available globally

    def test_is_product_available(self, db):
        """Test checking product availability in listing."""
        listing = Listing.objects.create(code="shop", name="Shop")
        product = Product.objects.create(sku="P1", name="Product 1")
        ListingItem.objects.create(listing=listing, product=product, price_q=500)

        assert CatalogService.is_product_available(product, "shop") is True
        assert CatalogService.is_product_available(product, "nonexistent") is False

    def test_listing_item_visibility(self, db):
        """Test listing item visibility flags."""
        listing = Listing.objects.create(code="shop", name="Shop")
        product = Product.objects.create(sku="P1", name="Product 1")
        ListingItem.objects.create(
            listing=listing, product=product, price_q=500,
            is_published=False,  # Unpublished in this listing
        )

        assert CatalogService.is_product_available(product, "shop") is False
