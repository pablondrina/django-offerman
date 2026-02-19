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
    'offerman',
    'offerman.contrib.admin_unfold',  # optional, for Unfold admin
]
```

```bash
python manage.py migrate
```

## Core Concepts

### Category
Hierarchical product classification.

```python
from offerman.models import Category

padaria = Category.objects.create(
    name="Padaria",
    slug="padaria",
)

paes = Category.objects.create(
    name="Paes",
    slug="paes",
    parent=padaria,
)
```

### Product
Sellable item with pricing and visibility controls.

```python
from offerman.models import Product

product = Product.objects.create(
    sku="PAO-FRANCES",
    name="Pao Frances",
    category=paes,
    base_price_q=80,  # R$ 0.80 in cents
    is_sellable=True,
)
```

### Collection
Flexible product grouping (non-hierarchical).

```python
from offerman.models import Collection

destaque = Collection.objects.create(
    slug="destaques",
    name="Produtos em Destaque",
)
destaque.products.add(product1, product2)
```

### PriceList
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
| `is_hidden` | Not shown in catalog | Seasonal items, internal products |
| `is_unavailable` | Shown but not purchasable | Out of stock, temporarily paused |

```python
# Hide product (not visible)
product.is_hidden = True

# Pause product (visible but not purchasable)
product.is_unavailable = True

# Check status
product.is_active      # not hidden AND not unavailable
product.is_visible     # not hidden
product.is_purchasable # not unavailable AND is_sellable
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
    quantity=Decimal("1"),
)

ProductComponent.objects.create(
    parent=combo,
    component=cafe,
    quantity=Decimal("1"),
)

# Check if bundle
combo.is_bundle  # True
```

## Price Resolution

Get product price for a channel:

```python
from offerman.services import get_price

# Get price from specific price list
price = get_price(product, price_list_code="ifood")

# Get best price (highest priority valid price list)
price = get_price(product)
```

## Integration with Omniman

Offerman provides a pricing backend for Omniman:

```python
# settings.py
OMNIMAN_PRICING_BACKEND = "omniman.contrib.pricing.PricingBackend"
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
- Bulk actions (hide/show, pause/resume)
- Inline components for bundles
- Price list item inlines

## Requirements

- Python 3.11+
- Django 5.0+
- django-taggit
- django-simple-history

## License

MIT
