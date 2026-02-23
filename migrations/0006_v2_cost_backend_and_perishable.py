"""
V2 Offerman improvements:
- Remove reference_cost_q (cost now via CostBackend Protocol)
- Replace shelflife (days) with shelf_life_hours (hours)
- Add production_cycle_hours
"""

from django.db import migrations, models


def convert_shelflife_to_hours(apps, schema_editor):
    """Convert shelflife (days) to shelf_life_hours (hours)."""
    Product = apps.get_model("offerman", "Product")
    for product in Product.objects.exclude(shelflife__isnull=True):
        product.shelf_life_hours = product.shelflife * 24
        product.save(update_fields=["shelf_life_hours"])


def convert_hours_to_shelflife(apps, schema_editor):
    """Reverse: convert shelf_life_hours back to shelflife (days)."""
    Product = apps.get_model("offerman", "Product")
    for product in Product.objects.exclude(shelf_life_hours__isnull=True):
        product.shelflife = product.shelf_life_hours // 24
        product.save(update_fields=["shelflife"])


class Migration(migrations.Migration):

    dependencies = [
        ("offerman", "0005_alter_collection_options_and_more"),
    ]

    operations = [
        # Step 1: Add new fields
        migrations.AddField(
            model_name="product",
            name="shelf_life_hours",
            field=models.IntegerField(
                blank=True,
                help_text="Validade em horas. Vazio=não perecível, 0=consumo imediato",
                null=True,
                verbose_name="validade (horas)",
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="production_cycle_hours",
            field=models.IntegerField(
                blank=True,
                help_text="Tempo de produção em horas (ex: 4h para croissant)",
                null=True,
                verbose_name="ciclo de produção (horas)",
            ),
        ),
        # Historical model fields
        migrations.AddField(
            model_name="historicalproduct",
            name="shelf_life_hours",
            field=models.IntegerField(
                blank=True,
                help_text="Validade em horas. Vazio=não perecível, 0=consumo imediato",
                null=True,
                verbose_name="validade (horas)",
            ),
        ),
        migrations.AddField(
            model_name="historicalproduct",
            name="production_cycle_hours",
            field=models.IntegerField(
                blank=True,
                help_text="Tempo de produção em horas (ex: 4h para croissant)",
                null=True,
                verbose_name="ciclo de produção (horas)",
            ),
        ),
        # Step 2: Data migration — convert shelflife days → shelf_life_hours
        migrations.RunPython(convert_shelflife_to_hours, convert_hours_to_shelflife),
        # Step 3: Remove old fields
        migrations.RemoveField(
            model_name="product",
            name="reference_cost_q",
        ),
        migrations.RemoveField(
            model_name="product",
            name="shelflife",
        ),
        migrations.RemoveField(
            model_name="historicalproduct",
            name="reference_cost_q",
        ),
        migrations.RemoveField(
            model_name="historicalproduct",
            name="shelflife",
        ),
    ]
