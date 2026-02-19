"""ProductComponent model."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


class ProductComponent(models.Model):
    """
    Component of a product.

    If a Product has components, it IS a bundle/combo.
    There is no separate Bundle model - the composition defines the bundle.
    """

    parent = models.ForeignKey(
        "offerman.Product",
        on_delete=models.CASCADE,
        related_name="components",
        verbose_name=_("produto pai"),
    )
    component = models.ForeignKey(
        "offerman.Product",
        on_delete=models.PROTECT,
        related_name="used_in_bundles",
        verbose_name=_("componente"),
    )
    qty = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        default=Decimal("1"),
        verbose_name=_("quantidade"),
    )

    class Meta:
        verbose_name = _("Componente de Produto")
        verbose_name_plural = _("Componentes de Produto")
        unique_together = [["parent", "component"]]

    def __str__(self):
        return f"{self.qty}x {self.component.sku} em {self.parent.sku}"

    def clean(self):
        """Validation: cannot be component of itself."""
        if self.parent_id == self.component_id:
            raise ValidationError("Product cannot be component of itself")

        # Check for circular reference
        if self._has_circular_reference():
            raise ValidationError("Circular component reference detected")

    def _has_circular_reference(self) -> bool:
        """Check if adding this component creates a circular reference."""
        visited = {self.parent_id}

        def check_descendants(product_id):
            if product_id in visited:
                return True
            visited.add(product_id)

            # Get components of this product
            components = ProductComponent.objects.filter(parent_id=product_id)
            for comp in components:
                if check_descendants(comp.component_id):
                    return True
            return False

        # Check if parent appears in component's descendants
        return check_descendants(self.component_id)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
