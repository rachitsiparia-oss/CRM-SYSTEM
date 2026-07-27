"""Inventory item code generation.

A tiny dedicated module (rather than inlining this in the router) so
`app/inventory/seed.py` and tests can generate the same shape of code
without importing FastAPI-layer code.
"""

import uuid


def generate_item_code() -> str:
    return f"ITM-{uuid.uuid4().hex[:8].upper()}"
