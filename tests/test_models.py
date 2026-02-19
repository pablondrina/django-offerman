"""Tests for Offerman models."""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from offerman.models import (
    Collection,
    CollectionItem,
    Product,
    ProductComponent,
    Listing,
    ListingItem,
)


pytestmark = pytest.mark.django_db


class TestProduct:
    """Tests for Product model."""

    def test_create_product(self, db):
        """Test product creation."""
        product = Product.objects.create(
            sku="BAGUETE",
            name="Baguete Artesanal",
            base_price_q=500,
        )
        assert product.sku == "BAGUETE"
        assert product.base_price_q == 500
        assert product.is_published is True
        assert product.is_available is True

    def test_base_price_property(self, db):
        """Test base_price property conversion."""
        product = Product.objects.create(
            sku="TEST",
            name="Test",
            base_price_q=500,
        )
        assert product.base_price == Decimal("5.00")

        product.base_price = Decimal("7.50")
        assert product.base_price_q == 750

    def test_queryset_active_method(self, db):
        """Test ProductQuerySet.active() method."""
        Product.objects.create(sku="P1", name="P1")  # published + available
        Product.objects.create(sku="P2", name="P2", is_published=False)  # unpublished
        Product.objects.create(sku="P3", name="P3", is_available=False)  # unavailable

        active = Product.objects.active()
        assert active.count() == 1
        assert active.first().sku == "P1"

    def test_queryset_published_method(self, db):
        """Test ProductQuerySet.published() method."""
        Product.objects.create(sku="P1", name="P1")
        Product.objects.create(sku="P2", name="P2", is_published=False)

        published = Product.objects.published()
        assert published.count() == 1
        assert published.first().sku == "P1"

    def test_queryset_available_method(self, db):
        """Test ProductQuerySet.available() method."""
        Product.objects.create(sku="P1", name="P1")
        Product.objects.create(sku="P2", name="P2", is_available=False)

        available = Product.objects.available()
        assert available.count() == 1
        assert available.first().sku == "P1"

    def test_is_bundle_property(self, db):
        """Test is_bundle property."""
        product = Product.objects.create(sku="SINGLE", name="Single")
        combo = Product.objects.create(sku="COMBO", name="Combo")
        croissant = Product.objects.create(sku="CROISSANT", name="Croissant")

        ProductComponent.objects.create(parent=combo, component=croissant, qty=Decimal("2"))

        assert product.is_bundle is False
        assert combo.is_bundle is True

    def test_margin_percent(self, db):
        """Test margin_percent calculation."""
        product = Product.objects.create(
            sku="MARGIN-TEST",
            name="Margin Test",
            base_price_q=1000,
            reference_cost_q=700,
        )
        assert product.margin_percent == Decimal("30.0")

    def test_margin_percent_no_cost(self, db):
        """Test margin_percent when no cost."""
        product = Product.objects.create(sku="NO-COST", name="No Cost")
        assert product.margin_percent is None


class TestProductComponent:
    """Tests for ProductComponent model."""

    def test_create_component(self, db):
        """Test component creation."""
        combo = Product.objects.create(sku="COMBO", name="Combo")
        croissant = Product.objects.create(sku="CROISSANT", name="Croissant")

        comp = ProductComponent.objects.create(
            parent=combo,
            component=croissant,
            qty=Decimal("2"),
        )
        assert comp.component == croissant
        assert comp.qty == Decimal("2")

    def test_self_reference_validation(self, db):
        """Test cannot be component of itself."""
        product = Product.objects.create(sku="SELF", name="Self")
        with pytest.raises(ValidationError):
            ProductComponent.objects.create(
                parent=product,
                component=product,
                qty=Decimal("1"),
            )

    def test_circular_reference_validation(self, db):
        """Test circular reference detection."""
        a = Product.objects.create(sku="A", name="A")
        b = Product.objects.create(sku="B", name="B")
        c = Product.objects.create(sku="C", name="C")

        # A contains B
        ProductComponent.objects.create(parent=a, component=b, qty=Decimal("1"))
        # B contains C
        ProductComponent.objects.create(parent=b, component=c, qty=Decimal("1"))

        # C cannot contain A (circular)
        with pytest.raises(ValidationError):
            ProductComponent.objects.create(parent=c, component=a, qty=Decimal("1"))


class TestListing:
    """Tests for Listing model."""

    def test_create_listing(self, db):
        """Test listing creation."""
        listing = Listing.objects.create(
            code="ifood",
            name="iFood",
        )
        assert listing.code == "ifood"
        assert listing.is_active is True

    def test_is_valid(self, db):
        """Test is_valid method."""
        from datetime import date, timedelta

        listing = Listing.objects.create(
            code="seasonal",
            name="Seasonal",
            valid_from=date.today() - timedelta(days=1),
            valid_until=date.today() + timedelta(days=1),
        )
        assert listing.is_valid() is True

        # Expired
        listing.valid_until = date.today() - timedelta(days=1)
        assert listing.is_valid() is False

    def test_is_valid_inactive(self, db):
        """Test is_valid returns False when inactive."""
        listing = Listing.objects.create(code="inactive", name="Inactive", is_active=False)
        assert listing.is_valid() is False


class TestListingItem:
    """Tests for ListingItem model."""

    def test_create_item(self, db):
        """Test listing item creation."""
        listing = Listing.objects.create(code="default", name="Default")
        product = Product.objects.create(sku="PROD", name="Product")

        item = ListingItem.objects.create(
            listing=listing,
            product=product,
            price_q=600,
        )
        assert item.price_q == 600
        assert item.price == Decimal("6.00")

    def test_visibility_flags(self, db):
        """Test is_published and is_available flags."""
        listing = Listing.objects.create(code="test", name="Test")
        product = Product.objects.create(sku="PROD", name="Product")

        item = ListingItem.objects.create(
            listing=listing,
            product=product,
            price_q=500,
            is_published=False,
            is_available=True,
        )
        assert item.is_published is False
        assert item.is_available is True


class TestCollection:
    """Tests for Collection model."""

    def test_create_collection(self, db):
        """Test collection creation."""
        collection = Collection.objects.create(
            slug="destaques",
            name="Destaques",
        )
        assert collection.slug == "destaques"
        assert collection.is_active is True

    def test_hierarchy(self, db):
        """Test collection hierarchy."""
        parent = Collection.objects.create(slug="breads", name="Breads")
        child = Collection.objects.create(slug="sweet-breads", name="Sweet Breads", parent=parent)

        assert child.parent == parent
        assert child.depth == 1
        assert parent.depth == 0

    def test_full_path(self, db):
        """Test full_path property."""
        parent = Collection.objects.create(slug="breads", name="Breads")
        child = Collection.objects.create(slug="sweet-breads", name="Sweet Breads", parent=parent)

        assert parent.full_path == "Breads"
        assert child.full_path == "Breads > Sweet Breads"

    def test_is_valid(self, db):
        """Test is_valid method."""
        from datetime import date, timedelta

        coll = Collection.objects.create(
            slug="natal",
            name="Christmas",
            valid_from=date.today() - timedelta(days=1),
            valid_until=date.today() + timedelta(days=1),
        )
        assert coll.is_valid() is True

        # Not yet started
        coll.valid_from = date.today() + timedelta(days=1)
        assert coll.is_valid() is False


class TestCollectionItem:
    """Tests for CollectionItem model."""

    def test_create_item(self, db):
        """Test collection item creation."""
        collection = Collection.objects.create(slug="test", name="Test")
        product = Product.objects.create(sku="PROD", name="Product")

        item = CollectionItem.objects.create(
            collection=collection,
            product=product,
            is_primary=True,
        )
        assert item.is_primary is True
        assert collection.items.count() == 1

    def test_single_primary(self, db):
        """Test only one primary collection per product."""
        col1 = Collection.objects.create(slug="col1", name="Col 1")
        col2 = Collection.objects.create(slug="col2", name="Col 2")
        product = Product.objects.create(sku="PROD", name="Product")

        # First item is primary
        item1 = CollectionItem.objects.create(
            collection=col1,
            product=product,
            is_primary=True,
        )
        assert item1.is_primary is True

        # Second item as primary should clear first
        item2 = CollectionItem.objects.create(
            collection=col2,
            product=product,
            is_primary=True,
        )
        item1.refresh_from_db()

        assert item2.is_primary is True
        assert item1.is_primary is False
