# Django Offerman

Product catalog and pricing for Django.

## Installation

```bash
pip install django-offerman
```

```python
INSTALLED_APPS = [
    ...
    'taggit',  # required
    'simple_history',  # required
    'offerman',
    'offerman.contrib.admin_unfold',  # optional, for Unfold admin
]
```

```bash
python manage.py migrate
```

## Core Concepts

### Collection

Unified product grouping (hierarchical or flat, with optional temporal validity).

```python
from offerman.models import Collection

padaria = Collection.objects.create(
    slug="padaria",
    name="Padaria",
)

paes = Collection.objects.create(
    slug="paes",
    name="Paes",
    parent=padaria,
)

# Hierarchy
paes.full_path       # "Padaria > Paes"
paes.depth           # 1
padaria.get_descendants()  # [paes, ...]
```

### Product

Sellable item with pricing and availability controls.

```python
from offerman.models import Product

product = Product.objects.create(
    sku="PAO-FRANCES",
    name="Pao Frances",
    base_price_q=80,  # R$ 0.80 in cents
    unit="un",
)
```

### CollectionItem

Associate products with collections:

```python
from offerman.models import CollectionItem

CollectionItem.objects.create(
    collection=paes,
    product=product,
    is_primary=True,  # primary collection for this product
)
```

### PriceList (Listing)

Channel-specific pricing.

```python
from offerman.models import PriceList, PriceListItem

ifood = PriceList.objects.create(
    code="ifood",
    name="Precos iFood",
    priority=10,  # higher = more specific
)

PriceListItem.objects.create(
    price_list=ifood,
    product=product,
    price_q=100,  # R$ 1.00 (20% mais caro)
)
```

## Visibility Control

Products have two visibility flags:

| Flag | Meaning | Use Case |
|------|---------|----------|
| `is_published` | Shown in catalog | Set False for hidden/discontinued items |
| `is_available` | Available for sale | Set False for paused or ingredient-only items |

```python
# Unpublish product (hidden from catalog)
product.is_published = False

# Pause product (visible but not for sale)
product.is_available = False

# QuerySet filters
Product.objects.active()     # is_published=True AND is_available=True
Product.objects.published()  # is_published=True
Product.objects.available()  # is_available=True
```

## Bundles/Combos

Products can have components (for bundles/combos):

```python
from offerman.models import ProductComponent

combo = Product.objects.create(
    sku="COMBO-CAFE",
    name="Combo Cafe da Manha",
    base_price_q=1500,
)

ProductComponent.objects.create(
    parent=combo,
    component=croissant,
    qty=Decimal("1"),
)

ProductComponent.objects.create(
    parent=combo,
    component=cafe,
    qty=Decimal("1"),
)

# Check if bundle
combo.is_bundle  # True
```

Circular references are detected automatically via `save()` -> `full_clean()`.

## Price Resolution

Get product price via CatalogService:

```python
from offerman.service import CatalogService

# Base price
price = CatalogService.price("PAO-FRANCES")

# Channel-specific price (from PriceList)
price = CatalogService.price("PAO-FRANCES", channel="ifood")

# With quantity
price = CatalogService.price("PAO-FRANCES", qty=Decimal("10"))
```

## Integration with Omniman

Offerman provides a CatalogBackend for Omniman:

```python
from offerman.adapters.catalog_backend import OffermanCatalogBackend

backend = OffermanCatalogBackend()
product_info = backend.get_product("PAO-FRANCES")
price_info = backend.get_price("PAO-FRANCES", qty=Decimal("3"))
```

## Keywords/Tags

Products support keywords via `django-taggit`:

```python
product.keywords.add("artesanal", "sem-gluten")
product.keywords.all()
```

## History Tracking

Offerman uses `django-simple-history` for audit trails on:
- Product (price changes, status changes)
- PriceListItem (price history)

```python
# View price history
for record in product.history.all():
    print(f"{record.history_date}: R$ {record.base_price_q / 100:.2f}")
```

## Admin (Unfold)

```python
INSTALLED_APPS = [
    'unfold',
    ...
    'offerman',
    'offerman.contrib.admin_unfold',
]
```

Features:
- Colored visibility badges
- Bulk actions (publish/unpublish, enable/disable)
- Inline components for bundles
- Price list item inlines

## Shopman Suite

Offerman is part of the Shopman Suite. The admin UI uses shared utilities from django-shopman-commons:

- `unfold_badge` — colored badge helpers
- `AutofillInlineMixin` — auto-fill inline fields from autocomplete data

```python
from commons.contrib.admin_unfold.badges import unfold_badge
from commons.admin.mixins import AutofillInlineMixin
```

### AutofillInlineMixin

Auto-fills inline fields from autocomplete selection data (Select2 cache).

```python
class ListingItemInline(AutofillInlineMixin, admin.TabularInline):
    model = ListingItem
    autocomplete_fields = ["product"]
    autofill_fields = {"product": {"price_q": "base_price_q"}}
```

When the user selects a product, `price_q` is filled with the
product's `base_price_q`. Target fields become optional automatically.

## Requirements

- Python 3.11+
- Django 5.0+
- django-taggit
- django-simple-history

## License

MIT
