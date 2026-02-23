# Offerman Contracts

> django-offerman v0.3 -- Product catalog and pricing for Django.

## Public API: CatalogService

All methods are `@classmethod` on `offerman.service.CatalogService`.

### Core Methods

| Method | Signature | Returns | Raises |
|--------|-----------|---------|--------|
| `get` | `get(sku: str) -> Product \| None` | Single product or `None` | -- |
| `get` | `get(sku: list[str]) -> dict[str, Product]` | Map of SKU to Product (missing SKUs omitted) | -- |
| `price` | `price(sku, qty=1, channel=None, price_list=None) -> int` | Total price in centavos (unit_price * qty) | `CatalogError("SKU_NOT_FOUND")`, `CatalogError("INVALID_QUANTITY")` |
| `expand` | `expand(sku, qty=1) -> list[dict]` | `[{"sku": str, "name": str, "qty": Decimal}, ...]` | `CatalogError("SKU_NOT_FOUND")`, `CatalogError("NOT_A_BUNDLE")` |
| `validate` | `validate(sku) -> SkuValidation` | Dataclass with `valid`, `sku`, `name`, `is_published`, `is_available`, `error_code`, `message` | -- |

### Convenience Methods

| Method | Signature | Returns |
|--------|-----------|---------|
| `search` | `search(query=None, collection=None, keywords=None, only_published=True, only_available=True, limit=20) -> list[Product]` | Filtered product list (name/SKU icontains, collection slug, keyword tags) |

### Listing / Channel Methods

| Method | Signature | Returns |
|--------|-----------|---------|
| `get_available_products` | `get_available_products(listing_code) -> QuerySet[Product]` | Products where global AND per-channel flags are all True |
| `is_product_available` | `is_product_available(product, listing_code) -> bool` | True if product is available in the given listing |

### CatalogError

Structured exception inheriting from `shopman_commons.exceptions.BaseError`.
Error codes: `SKU_NOT_FOUND`, `SKU_INACTIVE`, `NOT_A_BUNDLE`, `INVALID_PRICE_LIST`, `PRICE_LIST_EXPIRED`, `INVALID_QUANTITY`, `CIRCULAR_COMPONENT`.
Access `e.code` for the error code and `e.sku` for the associated SKU.

---

## Invariants

### Prices Stored as Integers

All prices are stored as `BigIntegerField` with the `_q` suffix (centavos).
`base_price_q`, `price_q`, cost values from `CostBackend` -- all integers.
Conversion to `Decimal` currency units: `Decimal(value_q) / 100`.
Conversion from `Decimal` to centavos: `int((Decimal(str(value)) * 100).to_integral_value(rounding=ROUND_HALF_UP))`.
Rounding is always `ROUND_HALF_UP`. There are no floating-point values in the pricing pipeline.

### Bundle Pricing

- A product is a bundle if it has `ProductComponent` rows (`product.components.exists()`).
- There is no separate Bundle model; composition defines the bundle.
- `expand()` returns one level of components with `qty * bundle_qty`.
- Cycle detection: `ProductComponent.clean()` walks the component graph with a `visited` set. If a product ID appears twice, `ValidationError("Circular component reference detected")` is raised.
- Depth limit: controlled by `OFFERMAN["BUNDLE_MAX_DEPTH"]` (default 5). Checked on every `ProductComponent.save()` via `full_clean()`.
- Self-reference: `parent_id == component_id` is rejected immediately.

### Listing Validity

- A `Listing` is valid when `is_active=True` AND the current date falls within `[valid_from, valid_until]` (both optional/nullable).
- `ListingItem` has per-channel `is_published` and `is_available` flags, independent of the global product flags.
- A product is available in a channel only when ALL five flags are True: `Product.is_published`, `Product.is_available`, `Listing.is_active`, `ListingItem.is_published`, `ListingItem.is_available`.
- Price resolution priority: when `channel` or `price_list` is provided to `CatalogService.price()`, the system finds the `Listing` by code, then selects the `ListingItem` with the highest `min_qty` that is still `<= qty`. If no matching listing/item is found, it falls back to `product.base_price_q`.
- Listings are ordered by `-priority, name`. Higher priority = more specific.

### Collection Hierarchy

- Collections support optional parent-child hierarchy (self-referencing FK).
- Max depth enforced by `OFFERMAN["MAX_COLLECTION_DEPTH"]` (default 10), checked in `Collection.clean()` on every `save()`.
- Circular references prevented: `clean()` walks the parent chain with a `visited` set and raises `ValidationError("Circular reference detected.")` on cycle.
- Each product may belong to multiple collections via `CollectionItem`, but only ONE can be marked `is_primary=True` (enforced by `UniqueConstraint` with condition).
- Temporal validity: collections have optional `valid_from`/`valid_until` date fields. `is_valid(date)` checks both `is_active` and the date range.

---

## Idempotency

| Operation | Safe to Retry | Notes |
|-----------|---------------|-------|
| `CatalogService.get()` | Yes | Read-only |
| `CatalogService.price()` | Yes | Read-only |
| `CatalogService.expand()` | Yes | Read-only |
| `CatalogService.validate()` | Yes | Read-only |
| `CatalogService.search()` | Yes | Read-only |
| `CatalogService.get_available_products()` | Yes | Read-only |
| `CatalogService.is_product_available()` | Yes | Read-only |
| `Product.save()` | Conditional | First save fires `product_created` signal; subsequent saves do not. Idempotent on updates. |
| `ListingItem.save()` | Conditional | Fires `price_changed` signal only when `price_q` actually changes. Re-saving with same price is idempotent. |
| `CollectionItem.save()` | Yes | Setting `is_primary=True` clears other primaries for the same product. Repeating the same save is idempotent. |

All `CatalogService` read methods are fully idempotent and safe to retry without side effects.

---

## Integration Points

### CostBackend Protocol

**Protocol**: `offerman.protocols.cost.CostBackend`
**Method**: `get_cost(sku: str) -> int | None`
**Configuration**: `OFFERMAN["COST_BACKEND"]` -- dotted path to a class implementing the protocol.
**Lifecycle**: Lazy singleton, instantiated on first access via `conf.get_cost_backend()`.
**Purpose**: Allows external apps (e.g., Craftsman) to provide production cost data without Offerman importing them. Used by `Product.reference_cost_q` and `Product.margin_percent`.

### CatalogBackend Protocol

**Protocol**: `offerman.protocols.catalog.CatalogBackend`
**Implementation**: `offerman.adapters.catalog_backend.OffermanCatalogBackend`
**Methods**: `get_product`, `get_price`, `validate_sku`, `expand_bundle`
**Purpose**: Allows other apps (Omniman, Stockman) to query the catalog through a protocol-based interface, without direct model imports.

### SKU Validator Adapter

**Class**: `offerman.adapters.sku_validator.OffermanSkuValidator`
**Consumer**: Stockman (`STOCKMAN["SKU_VALIDATOR"]` setting)
**Methods**: `validate_sku`, `validate_skus` (batch), `get_sku_info`, `search_skus`
**Purpose**: Lets Stockman validate SKUs against the Offerman catalog.

### Product Info Adapter

**Class**: `offerman.adapters.product_info.OffermanProductInfoBackend`
**Consumer**: Craftsman (`CRAFTSMAN["PRODUCT_INFO_BACKEND"]` setting)
**Methods**: `get_product_info`, `validate_output_sku`, `get_product_infos` (batch), `search_products`
**Purpose**: Lets Craftsman get product information and validate production output SKUs.

All adapters use thread-safe singleton factories with double-checked locking.

---

## What is NOT Offerman's Job

Offerman is strictly the product catalog and pricing layer. It does NOT handle:

- **Inventory / Stock** -- Managed by Stockman. Offerman provides `availability_policy` as a hint, but does not track quantities.
- **Orders / Sales** -- Managed by Omniman. Offerman provides prices; order creation and lifecycle are external.
- **Customer Management** -- No customer model or customer-specific pricing logic. Channel-level pricing is the lowest granularity.
- **Production / Recipes** -- Managed by Craftsman. Cost data flows IN via `CostBackend`, but Offerman does not own it.
- **Payments / Billing** -- Entirely external.
- **Shipping / Fulfillment** -- Entirely external.

---

## Signals

### `product_created`

**Module**: `offerman.signals.product_created`
**Fired when**: A `Product` is saved for the first time (`self._state.adding` is True).
**Kwargs**:
- `sender`: `Product` class
- `instance`: The new `Product` instance
- `sku`: `str` -- the product SKU

**Contract**: Fired exactly once per product, inside `Product.save()`, after the database row exists. Handlers can safely read the instance. Signal is NOT fired on subsequent updates.

### `price_changed`

**Module**: `offerman.signals.price_changed`
**Fired when**: A `ListingItem` is saved and its `price_q` value differs from the previously stored value.
**Kwargs**:
- `sender`: `ListingItem` class
- `instance`: The `ListingItem` instance
- `listing_code`: `str` -- the listing code
- `sku`: `str` -- the product SKU
- `old_price_q`: `int` -- previous price in centavos
- `new_price_q`: `int` -- new price in centavos

**Contract**: Fired only when price actually changes (not on creation, not when re-saving with the same price). The new row is already persisted when the signal fires. Both old and new values are provided so handlers can compute deltas.
