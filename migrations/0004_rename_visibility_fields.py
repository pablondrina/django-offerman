# Generated manually for nomenclature refactoring
# Renames is_visible -> is_published, is_sellable -> is_available
# Reference: specs/REFACTOR_NOMENCLATURE.md, BUSINESS_RULES.md section 16

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("offerman", "0003_rename_description_to_long_description"),
    ]

    operations = [
        # Product
        migrations.RenameField(
            model_name="product",
            old_name="is_visible",
            new_name="is_published",
        ),
        migrations.RenameField(
            model_name="product",
            old_name="is_sellable",
            new_name="is_available",
        ),
        # HistoricalProduct (django-simple-history)
        migrations.RenameField(
            model_name="historicalproduct",
            old_name="is_visible",
            new_name="is_published",
        ),
        migrations.RenameField(
            model_name="historicalproduct",
            old_name="is_sellable",
            new_name="is_available",
        ),
        # ListingItem
        migrations.RenameField(
            model_name="listingitem",
            old_name="is_visible",
            new_name="is_published",
        ),
        migrations.RenameField(
            model_name="listingitem",
            old_name="is_sellable",
            new_name="is_available",
        ),
        # HistoricalListingItem (django-simple-history)
        migrations.RenameField(
            model_name="historicallistingitem",
            old_name="is_visible",
            new_name="is_published",
        ),
        migrations.RenameField(
            model_name="historicallistingitem",
            old_name="is_sellable",
            new_name="is_available",
        ),
    ]
