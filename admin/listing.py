"""Listing admin."""

from django.contrib import admin

from offerman.models import Listing, ListingItem


class ListingItemInline(admin.TabularInline):
    model = ListingItem
    extra = 1
    autocomplete_fields = ["product"]
    fields = ["product", "price_q", "min_qty", "is_published", "is_available"]


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = [
        "code",
        "name",
        "is_active",
        "valid_from",
        "valid_until",
        "priority",
        "items_count",
    ]
    list_filter = ["is_active"]
    search_fields = ["code", "name"]
    list_editable = ["is_active", "priority"]
    ordering = ["-priority", "name"]
    inlines = [ListingItemInline]

    fieldsets = [
        (None, {"fields": ("code", "name", "description")}),
        ("Validity", {"fields": ("valid_from", "valid_until")}),
        ("Settings", {"fields": ("priority", "is_active")}),
    ]

    def items_count(self, obj):
        return obj.items.count()

    items_count.short_description = "Items"
