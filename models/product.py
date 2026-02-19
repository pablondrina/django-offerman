"""Product model."""

import uuid as uuid_lib
from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords
from taggit.managers import TaggableManager


class AvailabilityPolicy(models.TextChoices):
    """Availability policy for stock checking."""

    STOCK_ONLY = "stock_only", _("Somente estoque")
    PLANNED_OK = "planned_ok", _("Aceita planejado")
    DEMAND_OK = "demand_ok", _("Aceita demanda")


class ProductQuerySet(models.QuerySet):
    """Custom QuerySet for Product with availability filters."""

    def active(self):
        """Products that are published AND available."""
        return self.filter(is_published=True, is_available=True)

    def published(self):
        """Products that are published (may be unavailable)."""
        return self.filter(is_published=True)

    def available(self):
        """Products that are available for sale."""
        return self.filter(is_available=True)


class Product(models.Model):
    """Sellable product."""

    uuid = models.UUIDField(default=uuid_lib.uuid4, editable=False, unique=True)

    # Identification
    sku = models.CharField(
        _("SKU"),
        max_length=100,
        unique=True,
        db_index=True,
    )
    name = models.CharField(_("nome"), max_length=200)
    short_description = models.CharField(
        _("descrição curta"),
        max_length=255,
        blank=True,
        help_text=_("Descrição resumida para listagens (máx. 255 caracteres)"),
    )
    long_description = models.TextField(
        _("descrição longa"),
        blank=True,
        help_text=_("Descrição completa do produto"),
    )

    # Keywords for SEO, search, and suggestions
    keywords = TaggableManager(
        blank=True,
        verbose_name=_("palavras-chave"),
        help_text=_("Tags para SEO e busca. Separe por vírgula."),
    )

    # Unit of measure
    unit = models.CharField(
        _("unidade"),
        max_length=20,
        default="un",
        help_text=_("un, kg, lt, etc."),
    )

    # Base price (in cents)
    base_price_q = models.BigIntegerField(
        _("preço base"),
        default=0,
        help_text=_("Preço base em centavos"),
    )

    # Availability policy (used by Stockman)
    availability_policy = models.CharField(
        _("política de disponibilidade"),
        max_length=20,
        choices=AvailabilityPolicy.choices,
        default=AvailabilityPolicy.PLANNED_OK,
    )

    # Reference cost (updated by Craftsman)
    reference_cost_q = models.BigIntegerField(
        _("custo de referência"),
        null=True,
        blank=True,
        help_text=_("Custo de produção em centavos (ref. Craftsman)"),
    )

    # Shelflife in days (None = non-perishable, 0 = same day only)
    shelflife = models.IntegerField(
        _("validade"),
        null=True,
        blank=True,
        help_text=_("Validade em dias. Vazio=não perecível, 0=somente no dia"),
    )

    # === PUBLICATION & AVAILABILITY ===
    is_published = models.BooleanField(
        _("publicado"),
        default=True,
        db_index=True,
        help_text=_("Publicado no catálogo (Não = oculto/descontinuado)"),
    )

    is_available = models.BooleanField(
        _("disponível"),
        default=True,
        db_index=True,
        help_text=_("Disponível para venda (Não = insumo ou pausado)"),
    )

    # Batch production flag
    is_batch_produced = models.BooleanField(
        _("produção em lote"),
        default=False,
        help_text=_("Produzido em lotes (para Craftsman)"),
    )

    # Metadata
    metadata = models.JSONField(
        _("metadados"),
        default=dict,
        blank=True,
    )

    # Audit
    created_at = models.DateTimeField(_("criado em"), auto_now_add=True)
    updated_at = models.DateTimeField(_("atualizado em"), auto_now=True)

    # History tracking
    history = HistoricalRecords()

    # Custom manager with QuerySet methods
    objects = ProductQuerySet.as_manager()

    class Meta:
        verbose_name = _("produto")
        verbose_name_plural = _("produtos")
        ordering = ["name"]
        indexes = [
            models.Index(fields=["sku"]),
            models.Index(fields=["is_published", "is_available"]),
        ]

    def __str__(self):
        return f"{self.sku} - {self.name}"

    @property
    def base_price(self) -> Decimal:
        """Base price in currency units."""
        return Decimal(self.base_price_q) / 100

    @base_price.setter
    def base_price(self, value: Decimal):
        self.base_price_q = int(value * 100)

    @property
    def reference_cost(self) -> Decimal | None:
        """Reference cost in currency units."""
        if self.reference_cost_q is None:
            return None
        return Decimal(self.reference_cost_q) / 100

    @property
    def is_bundle(self) -> bool:
        """True if has components (is a bundle/combo)."""
        return self.components.exists()

    @property
    def margin_percent(self) -> Decimal | None:
        """Margin percentage (if reference cost exists)."""
        if not self.reference_cost_q or not self.base_price_q:
            return None
        margin = self.base_price_q - self.reference_cost_q
        return Decimal(margin * 100 / self.base_price_q).quantize(Decimal("0.1"))

    @property
    def is_hidden(self) -> bool:
        """Compatibility property: True if not published."""
        return not self.is_published

    @is_hidden.setter
    def is_hidden(self, value: bool):
        """Compatibility setter: sets is_published to inverse."""
        self.is_published = not value
