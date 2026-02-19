"""
Offerman Admin with Unfold theme.

This module provides Unfold-styled admin classes for Offerman models.
To use, add 'offerman.contrib.admin_unfold' to INSTALLED_APPS after 'offerman'.

The admins will automatically unregister the basic admins and register
the Unfold versions.
"""

from django.contrib import admin
from django.utils.html import format_html
from unfold.decorators import display

from offerman.contrib.admin_unfold.base import BaseModelAdmin, BaseTabularInline
from offerman.models import (
    Collection,
    CollectionItem,
    Listing,
    ListingItem,
    Product,
    ProductComponent,
)


def _unfold_badge(text, color="base"):
    """Create Unfold badge with colored background."""
    base_classes = (
        "inline-block font-semibold h-6 leading-6 px-2 "
        "rounded-default whitespace-nowrap text-xs uppercase"
    )

    color_classes = {
        "base": "bg-base-100 text-base-700 dark:bg-base-500/20 dark:text-base-200",
        "red": "bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400",
        "green": "bg-green-100 text-green-700 dark:bg-green-500/20 dark:text-green-400",
        "yellow": "bg-yellow-100 text-yellow-700 dark:bg-yellow-500/20 dark:text-yellow-400",
        "blue": "bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400",
    }

    classes = f"{base_classes} {color_classes.get(color, color_classes['base'])}"
    return format_html('<span class="{}">{}</span>', classes, text)


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


class ListingItemInline(BaseTabularInline):
    model = ListingItem
    extra = 1
    autocomplete_fields = ["product"]
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
    readonly_fields = ["uuid", "created_at", "updated_at", "is_bundle", "margin_percent"]
    inlines = [ProductCollectionItemInline, ProductListingItemInline, ProductComponentInline]

    fieldsets = [
        (
            None,
            {"fields": ("sku", "name", "description", "keywords")},
        ),
        (
            "Price",
            {"fields": ("base_price_q", "reference_cost_q", "margin_percent")},
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
                    "shelflife",
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
            badges.append(_unfold_badge("Unpublished", "yellow"))
        if not obj.is_available:
            badges.append(_unfold_badge("Unavailable", "red"))

        if not badges:
            return _unfold_badge("Active", "green")

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
