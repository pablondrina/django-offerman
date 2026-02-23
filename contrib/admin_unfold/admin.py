"""
Offerman Admin with Unfold theme.

This module provides Unfold-styled admin classes for Offerman models.
To use, add 'offerman.contrib.admin_unfold' to INSTALLED_APPS after 'offerman'.

The admins will automatically unregister the basic admins and register
the Unfold versions.
"""

from django import forms
from django.contrib import admin
from django.utils.html import format_html
from unfold.decorators import display

from shopman_commons.admin.mixins import AutofillInlineMixin
from shopman_commons.contrib.admin_unfold.base import BaseModelAdmin, BaseTabularInline
from shopman_commons.contrib.admin_unfold.badges import unfold_badge
from offerman.models import (
    Collection,
    CollectionItem,
    Listing,
    ListingItem,
    Product,
    ProductComponent,
)



# Unregister basic admins
for model in [Collection, Listing, Product]:
    try:
        admin.site.unregister(model)
    except admin.sites.NotRegistered:
        pass


# =============================================================================
# COLLECTION ADMIN
# =============================================================================


class CollectionItemInline(BaseTabularInline):
    model = CollectionItem
    extra = 1
    autocomplete_fields = ["product"]
    fields = ["product", "is_primary", "sort_order"]

    # Unfold sortable inline (drag-and-drop)
    ordering_field = "sort_order"
    hide_ordering_field = True


@admin.register(Collection)
class CollectionAdmin(BaseModelAdmin):
    list_display = [
        "slug",
        "name",
        "parent",
        "is_active_badge",
        "valid_from",
        "valid_until",
        "products_count",
    ]
    list_filter = ["is_active", "parent"]
    search_fields = ["slug", "name"]
    ordering = ["sort_order", "name"]
    prepopulated_fields = {"slug": ("name",)}
    inlines = [CollectionItemInline]

    fieldsets = [
        (None, {"fields": ("slug", "name", "description")}),
        ("Hierarchy", {"fields": ("parent",)}),
        ("Validity", {"fields": ("valid_from", "valid_until")}),
        ("Settings", {"fields": ("sort_order", "is_active")}),
    ]

    @display(description="Active", boolean=True)
    def is_active_badge(self, obj):
        return obj.is_active

    @display(description="Products")
    def products_count(self, obj):
        return obj.items.count()


# =============================================================================
# LISTING ADMIN
# =============================================================================


class ListingItemInline(AutofillInlineMixin, BaseTabularInline):
    model = ListingItem
    extra = 1
    autocomplete_fields = ["product"]
    autofill_fields = {"product": {"price_q": "base_price_q"}}
    fields = ["product", "price_q", "min_qty", "is_published", "is_available"]


@admin.register(Listing)
class ListingAdmin(BaseModelAdmin):
    list_display = [
        "code",
        "name",
        "is_active_badge",
        "valid_from",
        "valid_until",
        "priority",
        "items_count",
    ]
    list_filter = ["is_active"]
    search_fields = ["code", "name"]
    list_editable = ["priority"]
    ordering = ["-priority", "name"]
    inlines = [ListingItemInline]

    fieldsets = [
        (None, {"fields": ("code", "name", "description")}),
        ("Validity", {"fields": ("valid_from", "valid_until")}),
        ("Settings", {"fields": ("priority", "is_active")}),
    ]

    def save_formset(self, request, form, formset, change):
        """Default price_q to product.base_price_q when left blank."""
        instances = formset.save(commit=False)
        for instance in instances:
            if isinstance(instance, ListingItem) and instance.product_id:
                if not instance.price_q:
                    instance.price_q = instance.product.base_price_q
            instance.save()
        for obj in formset.deleted_objects:
            obj.delete()
        formset.save_m2m()

    @display(description="Active", boolean=True)
    def is_active_badge(self, obj):
        return obj.is_active

    @display(description="Items")
    def items_count(self, obj):
        return obj.items.count()


# =============================================================================
# PRODUCT ADMIN
# =============================================================================


class ProductComponentInline(BaseTabularInline):
    model = ProductComponent
    fk_name = "parent"
    extra = 1
    autocomplete_fields = ["component"]


class ProductCollectionItemInline(BaseTabularInline):
    """Inline to manage product's collection memberships."""
    model = CollectionItem
    extra = 1
    autocomplete_fields = ["collection"]
    fields = ["collection", "is_primary", "sort_order"]

    # Unfold sortable inline (drag-and-drop)
    ordering_field = "sort_order"
    hide_ordering_field = True


class ProductListingItemInline(BaseTabularInline):
    """Inline to manage product's listing (per-channel pricing/visibility)."""
    model = ListingItem
    extra = 0
    fields = ["listing", "price_q", "is_published", "is_available", "min_qty"]
    readonly_fields = ["listing"]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Product)
class ProductAdmin(BaseModelAdmin):
    list_display = [
        "sku",
        "name",
        "formatted_price",
        "visibility_status",
        "is_bundle_display",
    ]
    list_filter = [
        "is_published",
        "is_available",
        "availability_policy",
    ]
    search_fields = ["sku", "name", "keywords__name"]
    readonly_fields = ["uuid", "created_at", "updated_at", "is_bundle", "margin_percent", "is_perishable"]
    inlines = [ProductCollectionItemInline, ProductListingItemInline, ProductComponentInline]

    fieldsets = [
        (
            None,
            {"fields": ("sku", "name", "short_description", "long_description", "keywords")},
        ),
        (
            "Price & Cost",
            {"fields": ("base_price_q", "margin_percent")},
        ),
        (
            "Publication & Availability",
            {
                "fields": ("is_published", "is_available"),
                "description": "is_published controls catalog publication, is_available controls purchase availability.",
            },
        ),
        (
            "Configuration",
            {
                "fields": (
                    "unit",
                    "availability_policy",
                    "shelf_life_hours",
                    "is_perishable",
                    "production_cycle_hours",
                    "is_batch_produced",
                )
            },
        ),
        (
            "Metadata",
            {
                "fields": ("metadata", "uuid", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    ]

    @display(description="Price")
    def formatted_price(self, obj):
        return f"R$ {obj.base_price_q / 100:.2f}"

    @display(description="Status")
    def visibility_status(self, obj):
        """Display visibility status with colored badges."""
        badges = []

        if not obj.is_published:
            badges.append(unfold_badge("Unpublished", "yellow"))
        if not obj.is_available:
            badges.append(unfold_badge("Unavailable", "red"))

        if not badges:
            return unfold_badge("Active", "green")

        return format_html(" ".join(str(b) for b in badges))

    @display(description="Bundle", boolean=True)
    def is_bundle_display(self, obj):
        return obj.is_bundle

    actions = ["unpublish_products", "publish_products", "pause_products", "resume_products"]

    @admin.action(description="Unpublish selected products")
    def unpublish_products(self, request, queryset):
        updated = queryset.update(is_published=False)
        self.message_user(request, f"{updated} product(s) unpublished.")

    @admin.action(description="Publish selected products")
    def publish_products(self, request, queryset):
        updated = queryset.update(is_published=True)
        self.message_user(request, f"{updated} product(s) published.")

    @admin.action(description="Pause selected products (unavailable)")
    def pause_products(self, request, queryset):
        updated = queryset.update(is_available=False)
        self.message_user(request, f"{updated} product(s) paused.")

    @admin.action(description="Resume selected products (available)")
    def resume_products(self, request, queryset):
        updated = queryset.update(is_available=True)
        self.message_user(request, f"{updated} product(s) resumed.")
