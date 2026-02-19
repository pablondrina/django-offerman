"""Offerman signals."""

from django.dispatch import Signal

# Product signals
product_created = Signal()  # sender=Product
product_updated = Signal()  # sender=Product, changes=dict
product_deactivated = Signal()  # sender=Product

# Visibility signals
product_hidden = Signal()  # sender=Product
product_shown = Signal()  # sender=Product
product_paused = Signal()  # sender=Product (is_unavailable=True)
product_resumed = Signal()  # sender=Product (is_unavailable=False)

# Price signals
price_changed = Signal()  # sender=Product, old_price_q=int, new_price_q=int

# Composition signals
component_added = Signal()  # sender=ProductComponent
component_removed = Signal()  # sender=ProductComponent
