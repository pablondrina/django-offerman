# Pricing in Offerman

## The Pricing Resolution Pipeline

When `CatalogService.price(sku, qty, channel)` is called, the price is resolved through a layered pipeline. Each layer can override the previous one.

### 1. Base Price (always present)

Every `Product` has a `base_price_q` field -- an integer representing the price in centavos. This is the fallback price when no channel-specific pricing exists.

```
Product.base_price_q = 1500   # R$15.00
```

### 2. Listing Lookup (channel or price_list)

If a `channel` or `price_list` argument is provided, the system looks for a `Listing` whose `code` matches:

```python
price = CatalogService.price("BAGUETE", qty=3, channel="ifood")
```

The resolution steps:

1. Find `Listing` with `code == "ifood"`.
2. Check that the listing is valid: `is_active=True` and current date within `[valid_from, valid_until]`.
3. Find `ListingItem` rows for this product in this listing, where `min_qty <= qty`, `is_published=True`, and `is_available=True`.
4. Select the item with the **highest** `min_qty` that still satisfies the quantity (quantity discount tiers).
5. Use that item's `price_q` as the unit price.

If any step fails (no listing, listing expired, no matching item), the pipeline falls back to `base_price_q`.

### 3. Channel Priority

Listings have a `priority` field (integer, higher = more specific). When multiple listings could match, ordering is `-priority, name`. The `price()` method takes an explicit `price_list` or `channel` argument, so resolution is deterministic -- there is no automatic priority-based selection across multiple listings. The priority field is used for ordering in admin and in `get_available_products` queries.

### 4. Final Calculation

The total price is always computed as:

```python
total_q = int(Decimal(str(unit_price_q * qty)).to_integral_value(rounding=ROUND_HALF_UP))
```

All arithmetic stays in integer centavos until the final multiplication, which uses `Decimal` for correct rounding.

---

## The `_q` Suffix Convention

All monetary fields use the `_q` suffix to indicate the value is stored as an **integer in centavos** (1/100 of the currency unit).

| Field | Type | Meaning |
|-------|------|---------|
| `Product.base_price_q` | `BigIntegerField` | Base price in centavos |
| `ListingItem.price_q` | `BigIntegerField` | Channel price in centavos |
| `CostBackend.get_cost()` | `int \| None` | Production cost in centavos |

### Why integers?

Floating-point arithmetic introduces rounding errors that accumulate across operations. By storing centavos as integers, Offerman guarantees exact arithmetic for addition, subtraction, and comparison. Multiplication by quantity may produce fractional centavos, which are resolved with `ROUND_HALF_UP`.

### Converting between representations

```python
from decimal import Decimal, ROUND_HALF_UP

# Centavos to currency (read)
price = Decimal(product.base_price_q) / 100     # 1500 -> Decimal("15.00")

# Currency to centavos (write)
product.base_price_q = int(
    (Decimal("15.00") * 100).to_integral_value(rounding=ROUND_HALF_UP)
)

# The Product model provides a convenience property:
product.base_price        # -> Decimal("15.00")
product.base_price = 15   # -> sets base_price_q = 1500
```

---

## Collection Hierarchy and Primary Collection Resolution

Products are grouped into `Collection` objects via the `CollectionItem` join table.

### Hierarchy

Collections support optional parent-child nesting (self-FK on `parent`). This allows structures like:

```
Padaria
  > Paes
    > Paes Artesanais
  > Doces
```

Depth is limited by `OFFERMAN["MAX_COLLECTION_DEPTH"]` (default 10). Circular references are detected and rejected on `save()`.

### Primary Collection

A product can belong to many collections, but exactly **one** can be marked as its primary collection (`CollectionItem.is_primary = True`). This is enforced by a conditional unique constraint:

```
UniqueConstraint(fields=["product"], condition=Q(is_primary=True))
```

The primary collection is used by adapters (`OffermanCatalogBackend`, `OffermanSkuValidator`, `OffermanProductInfoBackend`) to populate the `category` field in protocol dataclasses. This gives downstream apps a single canonical grouping per product.

### Temporal Collections

Collections have optional `valid_from` and `valid_until` date fields. Call `collection.is_valid(date)` to check if a collection is active and within its date range. This supports seasonal or promotional groupings.

---

## Bundle / Composite Product Pricing

A product is a bundle if it has one or more `ProductComponent` rows. There is no separate Bundle model.

### Expanding a Bundle

```python
components = CatalogService.expand("COMBO-CAFE", qty=2)
# [
#     {"sku": "CAFE-EXPRESSO", "name": "Cafe Expresso", "qty": Decimal("2")},
#     {"sku": "CROISSANT",     "name": "Croissant",     "qty": Decimal("2")},
# ]
```

Component quantities are multiplied by the requested bundle quantity.

### Bundle Price

The bundle's price is its own `base_price_q` (or listing price if available). It is NOT computed by summing component prices. This allows bundles to have discount pricing independent of their components.

### Depth and Cycle Protection

- **Self-reference**: A product cannot be a component of itself.
- **Cycles**: `ProductComponent.clean()` performs a depth-first traversal of the component graph using a `visited` set. If any product ID appears twice, a `ValidationError` is raised.
- **Max depth**: Controlled by `OFFERMAN["BUNDLE_MAX_DEPTH"]` (default 5). Enforced on every `ProductComponent.save()`.

---

## CostBackend

### What It Is

`CostBackend` is a protocol (Python `typing.Protocol`) that allows an external app to provide production cost data for products. Offerman reads cost; it never writes it.

```python
@runtime_checkable
class CostBackend(Protocol):
    def get_cost(self, sku: str) -> int | None:
        """Return production cost in centavos, or None if unknown."""
        ...
```

### When It Is Called

- `Product.reference_cost_q` -- reads cost from the backend.
- `Product.margin_percent` -- computes `(base_price_q - cost_q) / base_price_q * 100`.

Both are `@property` on `Product`, so cost is fetched on access, not stored on the model.

### How to Implement One

1. Create a class that satisfies the `CostBackend` protocol:

```python
# In your app (e.g., craftsman/adapters/offerman.py)
class CraftsmanCostBackend:
    def get_cost(self, sku: str) -> int | None:
        from craftsman.models import Recipe
        recipe = Recipe.objects.filter(output_sku=sku).first()
        return recipe.total_cost_q if recipe else None
```

2. Register it in Django settings:

```python
OFFERMAN = {
    "COST_BACKEND": "craftsman.adapters.offerman.CraftsmanCostBackend",
}
```

3. The backend is instantiated as a lazy singleton on first access. Call `offerman.conf.reset_cost_backend()` in tests to clear the singleton between test cases.

### No-op Default

If `COST_BACKEND` is not configured (or set to `None`), `get_cost_backend()` returns `None`, and `Product.reference_cost_q` returns `None`. No error is raised. For projects that want an explicit no-op, use `offerman.adapters.noop.NoopCostBackend`.
